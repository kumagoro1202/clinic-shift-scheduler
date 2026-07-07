"""ui/pages/shift_editing.py（P7-5）の AppTest による表示・保存動作確認。

ARCHITECTURE.md 4 章のテスト戦略（UI 層は Streamlit AppTest でヘッドレス検証）に
基づく。生成結果は `shift_generation.py` と同様に `st.session_state
["shift_generation_result"]` を経由するため、`at.session_state` へ事前に
セットしてから `at.run()` する（AppTest は st.data_editor のセル単位編集
シミュレーションに未対応なため、保存ボタンの検証は「読み込んだ行がそのまま
再構築される」ことの確認に留める。staff_management.py のテストと同様の理由）。
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE_PATH = REPO_ROOT / "02-src" / "ui" / "pages" / "shift_editing.py"
SAMPLE_CONFIG_PATH = REPO_ROOT / "config" / "samples" / "sample_clinic.yaml"
SAMPLE_STAFF_PATH = REPO_ROOT / "config" / "samples" / "sample_staff.yaml"
SAMPLE_SCHEDULE_PATH = REPO_ROOT / "config" / "samples" / "sample_schedule_202608.yaml"

# sample_clinic.yaml（mon, early パターン 08:30-17:30・休憩60分）に整合する
# 1名・1日分の最小スケジュール。area_a相当の必要人数は満たさないため
# HC-001（必要人数）違反が出ることを意図的な検証にも使う。
_PARTIAL_SCHEDULE = {
    "2026-08-03": {
        "スタッフA": {
            "pattern": "early",
            "work": [
                {"area": "reception", "start": "08:30", "end": "12:30"},
                {"area": "reception", "start": "13:30", "end": "17:30"},
            ],
            "break": {"start": "12:30", "end": "13:30"},
        },
    },
}


@pytest.fixture
def env(tmp_path, monkeypatch):
    config_target = tmp_path / "clinic.yaml"
    shutil.copy(SAMPLE_CONFIG_PATH, config_target)
    monkeypatch.setenv("CLINIC_CONFIG_PATH", str(config_target))

    staff_target = tmp_path / "staff.yaml"
    shutil.copy(SAMPLE_STAFF_PATH, staff_target)
    monkeypatch.setenv("CLINIC_STAFF_PATH", str(staff_target))

    schedule_target = tmp_path / "schedule.yaml"
    shutil.copy(SAMPLE_SCHEDULE_PATH, schedule_target)
    monkeypatch.setenv("CLINIC_SCHEDULE_PATH", str(schedule_target))


def test_shows_info_when_no_generation_result_yet(env):
    at = AppTest.from_file(str(PAGE_PATH))
    at.run(timeout=15)

    assert not at.exception
    assert at.title[0].value == "シフト編集"
    assert at.info
    assert "シフト生成" in at.info[0].value


def test_shows_info_when_result_is_infeasible(env):
    at = AppTest.from_file(str(PAGE_PATH))
    at.session_state["shift_generation_result"] = {"status": "INFEASIBLE", "schedule": None}
    at.run(timeout=15)

    assert not at.exception
    assert at.info


def test_shows_editor_and_violation_check_for_result(env):
    at = AppTest.from_file(str(PAGE_PATH))
    at.session_state["shift_generation_result"] = {
        "status": "OPTIMAL",
        "schedule": _PARTIAL_SCHEDULE,
    }
    at.run(timeout=15)

    assert not at.exception
    assert not at.info
    assert at.subheader[0].value == "ハード制約違反チェック"
    # rehab の必要人数（09:00-12:30）が誰にも充足されないため HC-001 違反が出る
    assert at.warning
    assert "件のハード制約違反があります" in at.warning[0].value
    # dataframe[0] は st.data_editor（編集テーブル）、dataframe[-1] が
    # 違反一覧テーブル（st.dataframe）
    violation_rows = at.dataframe[-1].value
    assert "hc001_understaffed" in set(violation_rows["種別"])


def test_no_violations_shown_when_schedule_is_fully_staffed(env):
    full_schedule = {
        "2026-08-03": {
            "スタッフA": {
                "pattern": "early",
                "work": [
                    {"area": "reception", "start": "08:30", "end": "12:30"},
                    {"area": "reception", "start": "13:30", "end": "17:30"},
                ],
                "break": {"start": "12:30", "end": "13:30"},
            },
            "スタッフB": {
                "pattern": "early",
                "work": [
                    {"area": "reception", "start": "08:30", "end": "12:30"},
                    {"area": "reception", "start": "13:30", "end": "17:30"},
                ],
                "break": {"start": "12:30", "end": "13:30"},
            },
            "スタッフC": {
                "pattern": "early",
                "work": [
                    {"area": "rehab", "start": "09:00", "end": "12:30"},
                    {"area": "rehab", "start": "15:30", "end": "17:30"},
                ],
                "break": {"start": "12:30", "end": "13:30"},
            },
        },
    }
    at = AppTest.from_file(str(PAGE_PATH))
    at.session_state["shift_generation_result"] = {
        "status": "OPTIMAL",
        "schedule": full_schedule,
    }
    at.run(timeout=15)

    assert not at.exception
    assert at.success
    assert "違反はありません" in at.success[0].value


def test_save_button_persists_edited_schedule_to_session_state(env):
    at = AppTest.from_file(str(PAGE_PATH))
    at.session_state["shift_generation_result"] = {
        "status": "OPTIMAL",
        "schedule": _PARTIAL_SCHEDULE,
    }
    at.run(timeout=15)

    at.button[0].click().run(timeout=15)

    assert not at.exception
    assert at.success
    assert "保存しました" in at.success[-1].value
    saved_schedule = at.session_state["shift_generation_result"]["schedule"]
    assert saved_schedule["2026-08-03"]["スタッフA"]["work"] == _PARTIAL_SCHEDULE[
        "2026-08-03"
    ]["スタッフA"]["work"]


def test_shows_error_for_missing_config_file(tmp_path, monkeypatch):
    monkeypatch.setenv("CLINIC_CONFIG_PATH", str(tmp_path / "does_not_exist.yaml"))
    monkeypatch.setenv("CLINIC_STAFF_PATH", str(SAMPLE_STAFF_PATH))
    monkeypatch.setenv("CLINIC_SCHEDULE_PATH", str(SAMPLE_SCHEDULE_PATH))

    at = AppTest.from_file(str(PAGE_PATH))
    at.session_state["shift_generation_result"] = {
        "status": "OPTIMAL",
        "schedule": _PARTIAL_SCHEDULE,
    }
    at.run(timeout=15)

    assert not at.exception
    assert at.error
    assert "読込に失敗" in at.error[0].value
