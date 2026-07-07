"""P6-3 月次カレンダーモデルのテスト。

テスト専用のサンプル設定（config/samples/sample_clinic.yaml・
config/samples/sample_schedule_202608.yaml）のみを使用する。実在データは使用しない。
"""

import dataclasses
from pathlib import Path

import pytest
from ortools.sat.python import cp_model

from scheduler import calendar, config_loader, constraints, engine

SAMPLE_CONFIG = (
    Path(__file__).resolve().parents[2] / "config" / "samples" / "sample_clinic.yaml"
)
SAMPLE_SCHEDULE = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "samples"
    / "sample_schedule_202608.yaml"
)


@pytest.fixture(scope="module")
def config():
    return config_loader.load_config(SAMPLE_CONFIG)


@pytest.fixture(scope="module")
def monthly(config):
    return calendar.load_monthly_schedule(SAMPLE_SCHEDULE, config)


@pytest.fixture(scope="module")
def calendar_days(config, monthly):
    return calendar.expand_month(config, monthly)


@pytest.fixture(scope="module")
def result(config):
    return engine.run_monthly(config, SAMPLE_SCHEDULE, time_limit_seconds=60.0)


# --- カレンダー展開 -----------------------------------------------------------


def test_expand_month_excludes_closed_and_applies_overrides(calendar_days):
    """曜日由来の休診日（日曜）とカレンダー例外（祝日・臨時休診）が除外されること。"""
    dates = {day.date for day in calendar_days}

    # 2026年8月の日曜（曜日由来の休診日）
    for sunday in ("2026-08-02", "2026-08-09", "2026-08-16", "2026-08-23", "2026-08-30"):
        assert sunday not in dates, f"{sunday}（日曜）は除外されるはずです"

    # カレンダー例外（祝日・臨時休診）。通常は診療日となる曜日を選んでいる
    assert "2026-08-11" not in dates, "祝日（カレンダー例外）は除外されるはずです"
    assert "2026-08-14" not in dates, "臨時休診（カレンダー例外）は除外されるはずです"

    # 31日 - 日曜5日 - カレンダー例外2日 = 24日
    assert len(calendar_days) == 24


def test_expand_month_all_includes_closed_days(config, monthly):
    """P7-6: `expand_month_all` は休診日も含めて全日を返すこと（Excel出力の
    休診日網掛け表示に使用する。`external/output-design.md` 4章）。"""
    all_days = calendar.expand_month_all(config, monthly)
    dates = {day.date for day in all_days}

    assert "2026-08-02" in dates  # 日曜（曜日由来の休診日）
    assert "2026-08-11" in dates  # 祝日（カレンダー例外）
    by_date = {day.date: day for day in all_days}
    assert by_date["2026-08-02"].day_type == "closed"
    assert by_date["2026-08-11"].day_type == "closed"
    assert by_date["2026-08-11"].reason == "祝日"

    # 31日分すべてを含む
    assert len(all_days) == 31


def test_expand_month_is_subset_of_expand_month_all(config, monthly, calendar_days):
    all_days = calendar.expand_month_all(config, monthly)
    assert set(d.date for d in calendar_days) <= set(d.date for d in all_days)
    assert all(d.day_type != "closed" for d in calendar_days)


def test_expand_month_day_type_from_weekday_template(calendar_days):
    """カレンダー例外がない日は、曜日テンプレートの day_type が適用されること。"""
    by_date = {day.date: day for day in calendar_days}

    assert by_date["2026-08-03"].day_type == "full"  # mon
    assert by_date["2026-08-03"].weekday == "mon"
    assert by_date["2026-08-06"].day_type == "half"  # thu
    assert by_date["2026-08-05"].day_type == "short"  # wed


def test_load_monthly_schedule_rejects_date_outside_month(config, tmp_path):
    bad_file = tmp_path / "bad_schedule.yaml"
    bad_file.write_text(
        """
schema_version: 2
target_month: "2026-08"
calendar_overrides:
  - { date: "2026-09-01", day_type: closed, reason: "対象月外" }
""",
        encoding="utf-8",
    )
    with pytest.raises(config_loader.ConfigError, match="対象月外"):
        calendar.load_monthly_schedule(bad_file, config)


def test_load_monthly_schedule_rejects_unknown_staff(config, tmp_path):
    bad_file = tmp_path / "bad_schedule.yaml"
    bad_file.write_text(
        """
schema_version: 2
target_month: "2026-08"
vacations:
  - { staff: "存在しないスタッフ", date: "2026-08-05", kind: full }
""",
        encoding="utf-8",
    )
    with pytest.raises(config_loader.ConfigError, match="存在しません"):
        calendar.load_monthly_schedule(bad_file, config)


def test_load_monthly_schedule_rejects_duplicate_vacation(config, tmp_path):
    bad_file = tmp_path / "bad_schedule.yaml"
    bad_file.write_text(
        """
schema_version: 2
target_month: "2026-08"
vacations:
  - { staff: "スタッフA", date: "2026-08-05", kind: full }
  - { staff: "スタッフA", date: "2026-08-05", kind: am }
""",
        encoding="utf-8",
    )
    with pytest.raises(config_loader.ConfigError, match="重複"):
        calendar.load_monthly_schedule(bad_file, config)


# --- 月次シフト生成（エンジン） -----------------------------------------------


def test_engine_run_monthly_returns_schedule(config, calendar_days, result):
    """月次モデルが解を返し、スケジュールのキーが日付であること。"""
    assert result["status"] in ("OPTIMAL", "FEASIBLE")
    assert result["schedule"] is not None
    expected_dates = {day.date for day in calendar_days}
    assert set(result["schedule"].keys()) == expected_dates
    # 祝日・臨時休診・日曜は対象外
    assert "2026-08-11" not in result["schedule"]
    assert "2026-08-14" not in result["schedule"]
    assert "2026-08-02" not in result["schedule"]


def _coverage(day_schedule, area_name, minute):
    count = 0
    for entry in day_schedule.values():
        for segment in entry["work"]:
            if segment["area"] != area_name:
                continue
            start = config_loader.parse_time(segment["start"])
            end = config_loader.parse_time(segment["end"])
            if start <= minute < end:
                count += 1
    return count


def test_monthly_headcount_requirements_satisfied(config, calendar_days, result):
    """HC-001: 月次モデルでも全エリアの必要人数（曜日別バンド）が満たされていること。"""
    step = config.slot_minutes
    for day in calendar_days:
        day_schedule = result["schedule"][day.date]
        for area in config.areas:
            for band in area.requirements[day.weekday]:
                for minute in range(band.window.start, band.window.end, step):
                    actual = _coverage(day_schedule, area.name, minute)
                    assert actual >= band.headcount, (
                        f"{day.date}({day.weekday}) {area.name} "
                        f"{config_loader.format_time(minute)} の配置人数 {actual} が "
                        f"必要人数 {band.headcount} を下回っています"
                    )


def test_monthly_full_day_vacation_respected(result):
    """HC-004: スタッフAの終日休暇（2026-08-05）に勤務が割り当てられないこと。"""
    day_schedule = result["schedule"]["2026-08-05"]
    assert "スタッフA" not in day_schedule


def test_monthly_am_vacation_respected(result):
    """HC-004: スタッフBの午前休（2026-08-20）に午前の配置がないこと。"""
    day_schedule = result["schedule"].get("2026-08-20", {})
    entry = day_schedule.get("スタッフB")
    if entry is None:
        return  # その日勤務しない解も許容（午前休のみが制約対象）
    for segment in entry["work"]:
        start = config_loader.parse_time(segment["start"])
        assert start >= config_loader.AM_PM_BOUNDARY_MINUTES, (
            "スタッフBの午前休の日に午前の配置が残っています"
        )


def test_monthly_hc005_no_assign_variable_for_unqualified_staff(config, calendar_days, monthly):
    """HC-005: 月次モデルでも配置不可エリアの assign 変数が生成されないこと。"""
    sm = constraints.build_monthly_model(config, calendar_days, monthly.vacations)

    unqualified_pairs = [
        (staff, area)
        for staff in config.staff
        for area in config.areas
        if not staff.qualifies(area)
    ]
    assert unqualified_pairs, "テスト前提: 配置不可の (staff, area) 組が存在しません"

    for staff, area in unqualified_pairs:
        leaked = [key for key in sm.assign if key[0] == staff.name and key[2] == area.name]
        assert not leaked, (
            f"{staff.name} は {area.name} に配置不可のはずですが、"
            f"月次モデルで assign 変数が生成されています: {leaked}"
        )


def _breaks_at_slot(sm, day_key):
    starts_at_slot: dict[int, list] = {}
    for (_, key, slot), var in sm.break_start.items():
        if key == day_key:
            starts_at_slot.setdefault(slot, []).append(var)
    return max(starts_at_slot.items(), key=lambda item: len(item[1]))


def test_monthly_hc006_on_prevents_simultaneous_breaks(config, calendar_days, monthly):
    """HC-006 厳格形 ON では、月次モデルでも同時複数名休憩が禁止されること。"""
    strict_config = dataclasses.replace(
        config,
        strict_single_break=dataclasses.replace(config.strict_single_break, enabled=True),
    )
    sm = constraints.build_monthly_model(strict_config, calendar_days, monthly.vacations)
    day_key = "2026-08-03"  # mon 相当

    _, vars_at_slot = _breaks_at_slot(sm, day_key)
    assert len(vars_at_slot) >= 2, "テスト前提: 同一スロットに休憩候補が2人分以上必要です"
    for var in vars_at_slot[:2]:
        sm.model.add(var == 1)

    solver = cp_model.CpSolver()
    status = solver.solve(sm.model)
    assert status == cp_model.INFEASIBLE, (
        "strict_single_break.enabled=True では月次モデルでも"
        "同一スロットの2名同時休憩は禁止されているはずです"
    )


def test_monthly_hc006_off_allows_simultaneous_breaks(config, calendar_days, monthly):
    """HC-006 厳格形 OFF（初期値）では、月次モデルでも同時休憩開始を禁止しないこと。"""
    assert config.strict_single_break.enabled is False
    sm = constraints.build_monthly_model(config, calendar_days, monthly.vacations)
    day_key = "2026-08-03"

    _, vars_at_slot = _breaks_at_slot(sm, day_key)
    assert len(vars_at_slot) >= 2, "テスト前提: 同一スロットに休憩候補が2人分以上必要です"
    for var in vars_at_slot[:2]:
        sm.model.add(var == 1)

    solver = cp_model.CpSolver()
    status = solver.solve(sm.model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
