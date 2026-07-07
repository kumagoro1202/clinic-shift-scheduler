"""staff_repository（P7-2）の読込・保存・検証テスト。"""

from pathlib import Path

import pytest
import yaml

from scheduler.staff_repository import (
    SKILL_KEYS,
    StaffValidationError,
    load_staff,
    save_staff,
)

SAMPLE_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "samples" / "sample_staff.yaml"
)


def test_load_staff_returns_flat_rows():
    rows = load_staff(SAMPLE_PATH)
    assert len(rows) == 5
    first = rows[0]
    assert first["name"] == "スタッフA"
    assert first["employment"] == "full_time"
    assert first["weekly_workdays"] == 6
    for key in SKILL_KEYS:
        assert key in first
    assert first["rehab"] == 70


def test_load_staff_missing_file_raises(tmp_path):
    with pytest.raises(StaffValidationError):
        load_staff(tmp_path / "does_not_exist.yaml")


def test_load_staff_rejects_unsupported_schema_version(tmp_path):
    path = tmp_path / "staff.yaml"
    path.write_text("schema_version: 1\nstaff: []\n", encoding="utf-8")
    with pytest.raises(StaffValidationError):
        load_staff(path)


def test_save_and_reload_round_trip(tmp_path):
    path = tmp_path / "staff.yaml"
    rows = [
        {
            "name": "テストスタッフ1",
            "employment": "full_time",
            "weekly_workdays": 5,
            "rehab": 50,
            "reception_am": 60,
            "reception_pm": 70,
            "general": 80,
        }
    ]
    save_staff(path, rows)

    reloaded = load_staff(path)
    assert reloaded == rows

    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    assert raw["schema_version"] == 2
    assert raw["staff"][0]["skills"]["rehab"] == 50


def test_save_rejects_duplicate_names(tmp_path):
    path = tmp_path / "staff.yaml"
    rows = [
        {
            "name": "スタッフX",
            "employment": "full_time",
            "weekly_workdays": 5,
            "rehab": 50,
            "reception_am": 50,
            "reception_pm": 50,
            "general": 50,
        },
        {
            "name": "スタッフX",
            "employment": "part_time",
            "weekly_workdays": 3,
            "rehab": 0,
            "reception_am": 40,
            "reception_pm": 40,
            "general": 40,
        },
    ]
    with pytest.raises(StaffValidationError, match="重複"):
        save_staff(path, rows)
    assert not path.exists()


def test_save_rejects_invalid_employment(tmp_path):
    path = tmp_path / "staff.yaml"
    rows = [
        {
            "name": "スタッフY",
            "employment": "contractor",
            "weekly_workdays": 5,
            "rehab": 50,
            "reception_am": 50,
            "reception_pm": 50,
            "general": 50,
        }
    ]
    with pytest.raises(StaffValidationError, match="勤務形態"):
        save_staff(path, rows)


def test_save_rejects_skill_out_of_range(tmp_path):
    path = tmp_path / "staff.yaml"
    rows = [
        {
            "name": "スタッフZ",
            "employment": "full_time",
            "weekly_workdays": 5,
            "rehab": 150,
            "reception_am": 50,
            "reception_pm": 50,
            "general": 50,
        }
    ]
    with pytest.raises(StaffValidationError, match="rehab"):
        save_staff(path, rows)


def test_save_rejects_weekly_workdays_out_of_range(tmp_path):
    path = tmp_path / "staff.yaml"
    rows = [
        {
            "name": "スタッフW",
            "employment": "full_time",
            "weekly_workdays": 8,
            "rehab": 50,
            "reception_am": 50,
            "reception_pm": 50,
            "general": 50,
        }
    ]
    with pytest.raises(StaffValidationError, match="週勤務日数"):
        save_staff(path, rows)


def test_save_rejects_empty_name(tmp_path):
    path = tmp_path / "staff.yaml"
    rows = [
        {
            "name": "",
            "employment": "full_time",
            "weekly_workdays": 5,
            "rehab": 50,
            "reception_am": 50,
            "reception_pm": 50,
            "general": 50,
        }
    ]
    with pytest.raises(StaffValidationError, match="スタッフ名"):
        save_staff(path, rows)
