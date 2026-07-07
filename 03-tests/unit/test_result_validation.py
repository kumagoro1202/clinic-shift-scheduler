"""P7-5 手動編集後のハード制約違反チェック（scheduler.result）のテスト。

`internal/data-model.md` 5 章の方針（ソルバー出力の検証と手動編集後の
チェックを同一実装で行う）に基づく検証関数 `validate_hard_constraints` を、
HC-001（必要人数）・HC-002（重複配置）・HC-003（パターン時間内・実働時間・
休憩・週勤務日数上限）・HC-004（休暇時間帯への配置）・スキル適性の観点で
検証する。実在データは使用しない。
"""

from __future__ import annotations

import pytest

from scheduler import config_loader
from scheduler.calendar import CalendarDay, DateVacation
from scheduler.result import validate_hard_constraints

# 1名構成・月(full, area_a必要人数1・09:00-12:00)と火(full, 必要人数なし)の
# 2日のみ営業。weekly_workdays=1のため2日出勤すると週勤務日数超過になる。
_MINIMAL_CONFIG_YAML = """
schema_version: 1
work_rules:
  binding_hours: 8
  break_minutes: 60
  working_hours: 7
  break_window: { start: "11:00", end: "14:00" }
slot_minutes: 30
day_types:
  mon: full
  tue: full
  wed: closed
  thu: closed
  fri: closed
  sat: closed
  sun: closed
shift_patterns:
  - name: day
    day_types: [full]
    start: "09:00"
    end: "17:00"
    break_minutes: 60
areas:
  - name: area_a
    required_skills: [area_a]
    requirements:
      mon:
        - { start: "09:00", end: "12:00", headcount: 1 }
      tue: []
      wed: []
      thu: []
      fri: []
      sat: []
      sun: []
  - name: area_b
    required_skills: [area_b]
    requirements:
      mon: []
      tue: []
      wed: []
      thu: []
      fri: []
      sat: []
      sun: []
staff:
  - name: "スタッフ1"
    employment: full_time
    weekly_workdays: 1
    skills: { area_a: 50, area_b: 0 }
    vacations: []
"""

_MON = CalendarDay(date="2026-08-03", weekday="mon", day_type="full")
_TUE = CalendarDay(date="2026-08-04", weekday="tue", day_type="full")


@pytest.fixture
def minimal_config(tmp_path):
    path = tmp_path / "minimal_clinic.yaml"
    path.write_text(_MINIMAL_CONFIG_YAML, encoding="utf-8")
    return config_loader.load_config(path)


def _valid_entry() -> dict:
    return {
        "pattern": "day",
        "work": [{"area": "area_a", "start": "09:00", "end": "12:00"}],
        "break": {"start": "12:00", "end": "13:00"},
    }


def test_no_violations_for_valid_schedule(minimal_config):
    schedule = {"2026-08-03": {"スタッフ1": _valid_entry()}}
    warnings = validate_hard_constraints(minimal_config, (_MON,), (), schedule)
    assert warnings == []


def test_hc001_understaffed_when_nobody_assigned(minimal_config):
    schedule = {"2026-08-03": {}}
    warnings = validate_hard_constraints(minimal_config, (_MON,), (), schedule)
    assert any(w.kind == "hc001_understaffed" for w in warnings)


def test_hc002_overlap_for_double_booked_time(minimal_config):
    entry = _valid_entry()
    entry["work"] = [
        {"area": "area_a", "start": "09:00", "end": "12:00"},
        {"area": "area_b", "start": "10:00", "end": "11:00"},
    ]
    schedule = {"2026-08-03": {"スタッフ1": entry}}
    warnings = validate_hard_constraints(minimal_config, (_MON,), (), schedule)
    assert any(w.kind == "hc002_overlap" for w in warnings)


def test_hc003_missing_break_when_pattern_requires_one(minimal_config):
    entry = _valid_entry()
    entry["break"] = None
    schedule = {"2026-08-03": {"スタッフ1": entry}}
    warnings = validate_hard_constraints(minimal_config, (_MON,), (), schedule)
    assert any(w.kind == "hc003_missing_break" for w in warnings)


def test_hc003_out_of_window_before_pattern_start(minimal_config):
    entry = _valid_entry()
    entry["work"] = [{"area": "area_a", "start": "08:00", "end": "09:00"}]
    schedule = {"2026-08-03": {"スタッフ1": entry}}
    warnings = validate_hard_constraints(minimal_config, (_MON,), (), schedule)
    assert any(w.kind == "hc003_out_of_window" for w in warnings)


def test_hc003_over_working_minutes(minimal_config):
    entry = _valid_entry()
    entry["work"] = [{"area": "area_a", "start": "09:00", "end": "17:00"}]
    entry["break"] = None
    schedule = {"2026-08-03": {"スタッフ1": entry}}
    warnings = validate_hard_constraints(minimal_config, (_MON,), (), schedule)
    assert any(w.kind == "hc003_over_working_minutes" for w in warnings)


def test_hc003_over_weekly_workdays(minimal_config):
    schedule = {
        "2026-08-03": {"スタッフ1": _valid_entry()},
        "2026-08-04": {"スタッフ1": _valid_entry()},
    }
    warnings = validate_hard_constraints(minimal_config, (_MON, _TUE), (), schedule)
    over_limit = [w for w in warnings if w.kind == "hc003_over_weekly_workdays"]
    assert len(over_limit) == 1
    assert "2日" in over_limit[0].detail


def test_hc004_vacation_violation_on_full_day_vacation(minimal_config):
    schedule = {"2026-08-03": {"スタッフ1": _valid_entry()}}
    vacations = (DateVacation(staff="スタッフ1", date="2026-08-03", kind="full"),)
    warnings = validate_hard_constraints(minimal_config, (_MON,), vacations, schedule)
    assert any(w.kind == "hc004_vacation_violation" for w in warnings)


def test_unqualified_area_assignment(minimal_config):
    entry = _valid_entry()
    entry["work"] = [{"area": "area_b", "start": "09:00", "end": "12:00"}]
    schedule = {"2026-08-03": {"スタッフ1": entry}}
    warnings = validate_hard_constraints(minimal_config, (_MON,), (), schedule)
    assert any(w.kind == "unqualified_area" for w in warnings)


def test_hc007_empty_attendance(minimal_config):
    schedule = {
        "2026-08-03": {"スタッフ1": {"pattern": "day", "work": [], "break": None}}
    }
    warnings = validate_hard_constraints(minimal_config, (_MON,), (), schedule)
    assert any(w.kind == "hc007_empty_attendance" for w in warnings)
