"""scheduler/infeasible_hints.py（P7-4）の要因手がかり算出テスト。

テスト専用のサンプル設定（config/samples/sample_clinic.yaml）のみを使用する。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scheduler import calendar, config_loader
from scheduler.infeasible_hints import (
    compute_headcount_deficit_hints,
    compute_vacation_concentration_hints,
)

SAMPLE_CONFIG = (
    Path(__file__).resolve().parents[2] / "config" / "samples" / "sample_clinic.yaml"
)


@pytest.fixture(scope="module")
def config():
    return config_loader.load_config(SAMPLE_CONFIG)


def _write_schedule(tmp_path, body: str) -> Path:
    path = tmp_path / "schedule.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_no_deficit_for_feasible_sample_schedule(config, tmp_path):
    schedule_path = _write_schedule(
        tmp_path,
        """
schema_version: 2
target_month: "2026-08"
vacations:
  - { staff: "スタッフA", date: "2026-08-05", kind: full }
""",
    )
    monthly = calendar.load_monthly_schedule(schedule_path, config)
    calendar_days = calendar.expand_month(config, monthly)

    assert compute_headcount_deficit_hints(config, calendar_days, monthly.vacations) == []


def test_deficit_detected_when_all_rehab_qualified_staff_on_vacation(config, tmp_path):
    """スタッフA・C・Dの3名がリハ室配置可能な全員。同日終日休暇で不足を検出できること。"""
    schedule_path = _write_schedule(
        tmp_path,
        """
schema_version: 2
target_month: "2026-08"
vacations:
  - { staff: "スタッフA", date: "2026-08-03", kind: full }
  - { staff: "スタッフC", date: "2026-08-03", kind: full }
  - { staff: "スタッフD", date: "2026-08-03", kind: full }
""",
    )
    monthly = calendar.load_monthly_schedule(schedule_path, config)
    calendar_days = calendar.expand_month(config, monthly)

    hints = compute_headcount_deficit_hints(config, calendar_days, monthly.vacations)
    assert hints
    assert all(h.date == "2026-08-03" and h.area == "rehab" for h in hints)
    assert all(h.available_count == 0 and h.deficit == h.required_headcount for h in hints)


def test_vacation_concentration_counts_same_day_vacations(config, tmp_path):
    schedule_path = _write_schedule(
        tmp_path,
        """
schema_version: 2
target_month: "2026-08"
vacations:
  - { staff: "スタッフA", date: "2026-08-03", kind: full }
  - { staff: "スタッフB", date: "2026-08-03", kind: am }
  - { staff: "スタッフE", date: "2026-08-05", kind: full }
""",
    )
    monthly = calendar.load_monthly_schedule(schedule_path, config)
    calendar_days = calendar.expand_month(config, monthly)

    hints = compute_vacation_concentration_hints(calendar_days, monthly.vacations)
    by_date = {h.date: h.vacation_count for h in hints}
    assert by_date["2026-08-03"] == 2
    assert by_date["2026-08-05"] == 1


def test_vacation_concentration_top_n_limits_results(config, tmp_path):
    lines = [
        f'  - {{ staff: "スタッフE", date: "2026-08-{day:02d}", kind: full }}'
        for day in range(3, 9)
        if day != 2
    ]
    schedule_path = _write_schedule(
        tmp_path,
        "schema_version: 2\ntarget_month: \"2026-08\"\nvacations:\n" + "\n".join(lines) + "\n",
    )
    monthly = calendar.load_monthly_schedule(schedule_path, config)
    calendar_days = calendar.expand_month(config, monthly)

    hints = compute_vacation_concentration_hints(calendar_days, monthly.vacations, top_n=3)
    assert len(hints) == 3
