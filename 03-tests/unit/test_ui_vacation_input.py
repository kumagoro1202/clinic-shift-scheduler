"""ui/pages/vacation_input.py（P7-3）の AppTest による表示・保存動作確認。

ARCHITECTURE.md 4 章のテスト戦略（UI 層は Streamlit AppTest でヘッドレス検証）に
基づく。データソースは環境変数 CLINIC_STAFF_PATH / CLINIC_SCHEDULE_PATH で
テスト用の一時ファイルへ差し替える（staff_management.py と同様の理由で
ファイルパス方式の st.Page は Python オブジェクトの直接差し替えができない）。
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE_PATH = REPO_ROOT / "02-src" / "ui" / "pages" / "vacation_input.py"
SAMPLE_STAFF_PATH = REPO_ROOT / "config" / "samples" / "sample_staff.yaml"
SAMPLE_SCHEDULE_PATH = REPO_ROOT / "config" / "samples" / "sample_schedule_202608.yaml"


@pytest.fixture
def schedule_yaml_copy(tmp_path, monkeypatch):
    staff_target = tmp_path / "staff.yaml"
    shutil.copy(SAMPLE_STAFF_PATH, staff_target)
    monkeypatch.setenv("CLINIC_STAFF_PATH", str(staff_target))

    schedule_target = tmp_path / "schedule.yaml"
    shutil.copy(SAMPLE_SCHEDULE_PATH, schedule_target)
    monkeypatch.setenv("CLINIC_SCHEDULE_PATH", str(schedule_target))
    return schedule_target


def test_vacation_input_shows_title_and_editor(schedule_yaml_copy):
    at = AppTest.from_file(str(PAGE_PATH))
    at.run(timeout=15)
    assert not at.exception
    assert at.title[0].value == "休暇入力"
    assert at.caption[0].value.startswith("日付単位の休暇登録")
    assert at.button[0].label == "保存"


def test_vacation_input_save_button_persists_rows(schedule_yaml_copy):
    at = AppTest.from_file(str(PAGE_PATH))
    at.run(timeout=15)

    at.button[0].click().run(timeout=15)

    assert not at.exception
    assert at.success
    assert "保存しました" in at.success[0].value
    saved = yaml.safe_load(schedule_yaml_copy.read_text(encoding="utf-8"))
    assert saved["schema_version"] == 2
    assert saved["target_month"] == "2026-08"
    # calendar_overrides は休暇入力画面からは変更されず、そのまま保持される
    assert len(saved["calendar_overrides"]) == 2
    assert {"staff": "スタッフA", "date": "2026-08-05", "kind": "full", "paid": True} in saved[
        "vacations"
    ]


def test_vacation_input_editor_shows_existing_vacations(schedule_yaml_copy):
    at = AppTest.from_file(str(PAGE_PATH))
    at.run(timeout=15)

    assert not at.exception
    editor_value = at.dataframe[0].value
    assert list(editor_value["staff"]) == ["スタッフA", "スタッフB"]
    assert list(editor_value["kind"]) == ["full", "am"]


def test_vacation_input_shows_error_for_missing_schedule_file(tmp_path, monkeypatch):
    staff_target = tmp_path / "staff.yaml"
    shutil.copy(SAMPLE_STAFF_PATH, staff_target)
    monkeypatch.setenv("CLINIC_STAFF_PATH", str(staff_target))
    monkeypatch.setenv("CLINIC_SCHEDULE_PATH", str(tmp_path / "does_not_exist.yaml"))

    at = AppTest.from_file(str(PAGE_PATH))
    at.run(timeout=15)

    assert not at.exception
    assert at.error
    assert "読込に失敗" in at.error[0].value
