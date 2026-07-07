"""ui/pages/shift_export.py（P7-6）の AppTest による表示・出力動作確認。

ARCHITECTURE.md 4章のテスト戦略（UI層はStreamlit AppTestでヘッドレス検証）に
基づく。生成結果は shift_editing.py 等と同様に
`st.session_state["shift_generation_result"]` を経由するため、
`at.session_state` へ事前にセットしてから `at.run()` する。
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE_PATH = REPO_ROOT / "02-src" / "ui" / "pages" / "shift_export.py"
SAMPLE_CONFIG_PATH = REPO_ROOT / "config" / "samples" / "sample_clinic.yaml"
SAMPLE_STAFF_PATH = REPO_ROOT / "config" / "samples" / "sample_staff.yaml"
SAMPLE_SCHEDULE_PATH = REPO_ROOT / "config" / "samples" / "sample_schedule_202608.yaml"

_SCHEDULE = {
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
    assert at.title[0].value == "Excel 出力・印刷"
    assert at.info
    assert "シフト生成" in at.info[0].value


def test_shows_download_button_for_result(env):
    """write_excel を実データパスで実行し、例外なくダウンロードボタンが
    表示されること（バイト内容の検証は test_excel_exporter.py で行う）。"""
    at = AppTest.from_file(str(PAGE_PATH))
    at.session_state["shift_generation_result"] = {
        "status": "OPTIMAL",
        "schedule": _SCHEDULE,
    }
    at.run(timeout=15)

    assert not at.exception
    assert not at.info
    assert at.download_button
    assert at.download_button[0].label == "Excel ファイルをダウンロード"


def test_orientation_and_paper_size_selectors_shown(env):
    at = AppTest.from_file(str(PAGE_PATH))
    at.session_state["shift_generation_result"] = {
        "status": "OPTIMAL",
        "schedule": _SCHEDULE,
    }
    at.run(timeout=15)

    assert not at.exception
    labels = [sb.label for sb in at.selectbox]
    assert "印刷の向き" in labels
    assert "用紙サイズ" in labels


def test_shows_error_for_missing_config_file(tmp_path, monkeypatch):
    monkeypatch.setenv("CLINIC_CONFIG_PATH", str(tmp_path / "does_not_exist.yaml"))
    monkeypatch.setenv("CLINIC_STAFF_PATH", str(SAMPLE_STAFF_PATH))
    monkeypatch.setenv("CLINIC_SCHEDULE_PATH", str(SAMPLE_SCHEDULE_PATH))

    at = AppTest.from_file(str(PAGE_PATH))
    at.session_state["shift_generation_result"] = {
        "status": "OPTIMAL",
        "schedule": _SCHEDULE,
    }
    at.run(timeout=15)

    assert not at.exception
    assert at.error
    assert "読込に失敗" in at.error[0].value
