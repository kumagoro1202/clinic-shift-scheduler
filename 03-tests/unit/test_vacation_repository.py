"""vacation_repository（P7-3）の読込・保存・検証テスト。"""

from pathlib import Path

import pytest
import yaml

from scheduler.vacation_repository import (
    VacationValidationError,
    load_schedule,
    save_schedule,
)

SAMPLE_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "samples" / "sample_schedule_202608.yaml"
)
STAFF_NAMES = ["スタッフA", "スタッフB", "スタッフC", "スタッフD", "スタッフE"]


def test_load_schedule_returns_target_month_and_vacations():
    schedule = load_schedule(SAMPLE_PATH)
    assert schedule["target_month"] == "2026-08"
    assert len(schedule["vacations"]) == 2
    first = schedule["vacations"][0]
    assert first["staff"] == "スタッフA"
    assert first["date"] == "2026-08-05"
    assert first["kind"] == "full"
    assert first["paid"] is True
    assert "calendar_overrides" in schedule["raw"]


def test_load_schedule_missing_file_raises(tmp_path):
    with pytest.raises(VacationValidationError):
        load_schedule(tmp_path / "does_not_exist.yaml")


def test_load_schedule_rejects_unsupported_schema_version(tmp_path):
    path = tmp_path / "schedule.yaml"
    path.write_text('schema_version: 1\ntarget_month: "2026-08"\n', encoding="utf-8")
    with pytest.raises(VacationValidationError):
        load_schedule(path)


def test_save_and_reload_round_trip_preserves_calendar_overrides(tmp_path):
    path = tmp_path / "schedule.yaml"
    path.write_text(SAMPLE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    schedule = load_schedule(path)

    new_rows = [{"staff": "スタッフC", "date": "2026-08-10", "kind": "am", "paid": False}]
    save_schedule(path, schedule["target_month"], new_rows, schedule["raw"], STAFF_NAMES)

    reloaded = load_schedule(path)
    assert reloaded["vacations"] == new_rows
    assert reloaded["raw"]["calendar_overrides"] == schedule["raw"]["calendar_overrides"]

    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    assert raw["schema_version"] == 2
    assert len(raw["calendar_overrides"]) == 2


def test_save_rejects_date_outside_target_month(tmp_path):
    path = tmp_path / "schedule.yaml"
    rows = [{"staff": "スタッフA", "date": "2026-09-01", "kind": "full", "paid": False}]
    with pytest.raises(VacationValidationError, match="対象月内"):
        save_schedule(path, "2026-08", rows, {}, STAFF_NAMES)
    assert not path.exists()


def test_save_rejects_unknown_staff(tmp_path):
    path = tmp_path / "schedule.yaml"
    rows = [{"staff": "存在しないスタッフ", "date": "2026-08-05", "kind": "full", "paid": False}]
    with pytest.raises(VacationValidationError, match="存在しません"):
        save_schedule(path, "2026-08", rows, {}, STAFF_NAMES)


def test_save_rejects_invalid_kind(tmp_path):
    path = tmp_path / "schedule.yaml"
    rows = [{"staff": "スタッフA", "date": "2026-08-05", "kind": "evening", "paid": False}]
    with pytest.raises(VacationValidationError, match="休暇種別"):
        save_schedule(path, "2026-08", rows, {}, STAFF_NAMES)


def test_save_rejects_duplicate_staff_date(tmp_path):
    path = tmp_path / "schedule.yaml"
    rows = [
        {"staff": "スタッフA", "date": "2026-08-05", "kind": "full", "paid": False},
        {"staff": "スタッフA", "date": "2026-08-05", "kind": "am", "paid": False},
    ]
    with pytest.raises(VacationValidationError, match="重複"):
        save_schedule(path, "2026-08", rows, {}, STAFF_NAMES)


def test_save_accepts_am_and_pm_kinds(tmp_path):
    path = tmp_path / "schedule.yaml"
    rows = [
        {"staff": "スタッフA", "date": "2026-08-05", "kind": "am", "paid": False},
        {"staff": "スタッフB", "date": "2026-08-06", "kind": "pm", "paid": True},
    ]
    save_schedule(path, "2026-08", rows, {}, STAFF_NAMES)
    reloaded = load_schedule(path)
    assert reloaded["vacations"] == rows
