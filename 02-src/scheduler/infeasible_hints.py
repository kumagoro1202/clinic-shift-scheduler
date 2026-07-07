"""INFEASIBLE 時の要因手がかり生成（P7-4, FR-03）。

CP-SAT ソルバーは INFEASIBLE の内部理由（どの制約が衝突したか）を直接
提供しないため、必要人数と「休暇等を考慮した配置可能人数」の差分を
ヒューリスティックに算出し、調査の手がかりとして提示する
（`external/output-design.md` 2 章の表示要件）。あくまで簡易な目安であり、
厳密な原因特定（IIS 等）ではない。
"""

from __future__ import annotations

from dataclasses import dataclass

from .calendar import CalendarDay, DateVacation
from .config_loader import AM_PM_BOUNDARY_MINUTES, Config, TimeRange, format_time


@dataclass(frozen=True)
class HeadcountDeficitHint:
    date: str
    weekday: str
    area: str
    window_start: str
    window_end: str
    required_headcount: int
    available_count: int
    deficit: int


@dataclass(frozen=True)
class VacationConcentrationHint:
    date: str
    weekday: str
    vacation_count: int


def _vacation_kind_by_staff_date(vacations: tuple[DateVacation, ...]) -> dict[tuple[str, str], str]:
    return {(v.staff, v.date): v.kind for v in vacations}


def _available_for_band(kind: str | None, window: TimeRange) -> bool:
    """休暇種別からみて、そのバンド（時間帯）に配置可能かを判定する。

    full: 終日不可。am: 境界時刻より前に終わるバンドは不可。
    pm: 境界時刻以降に始まるバンドは不可（`AM_PM_BOUNDARY_MINUTES` 基準）。
    """
    if kind is None:
        return True
    if kind == "full":
        return False
    if kind == "am":
        return window.start >= AM_PM_BOUNDARY_MINUTES
    if kind == "pm":
        return window.end <= AM_PM_BOUNDARY_MINUTES
    return True


def compute_headcount_deficit_hints(
    config: Config,
    calendar_days: tuple[CalendarDay, ...],
    vacations: tuple[DateVacation, ...],
    top_n: int = 5,
) -> list[HeadcountDeficitHint]:
    """曜日別必要人数に対し、休暇考慮後の配置可能人数が不足している上位を返す。

    date 単位休暇（`vacations`）を優先し、無ければスタッフマスタの曜日単位
    休暇（`staff.vacation_on`）を用いる。
    """
    vacation_kind = _vacation_kind_by_staff_date(vacations)
    hints: list[HeadcountDeficitHint] = []

    for day in calendar_days:
        for area in config.areas:
            for band in area.requirements.get(day.weekday, ()):
                if band.headcount <= 0:
                    continue
                available = 0
                for staff in config.staff:
                    if not staff.qualifies(area):
                        continue
                    kind = vacation_kind.get((staff.name, day.date))
                    if kind is None:
                        weekday_vacation = staff.vacation_on(day.weekday)
                        kind = weekday_vacation.kind if weekday_vacation else None
                    if _available_for_band(kind, band.window):
                        available += 1
                deficit = band.headcount - available
                if deficit > 0:
                    hints.append(
                        HeadcountDeficitHint(
                            date=day.date,
                            weekday=day.weekday,
                            area=area.name,
                            window_start=format_time(band.window.start),
                            window_end=format_time(band.window.end),
                            required_headcount=band.headcount,
                            available_count=available,
                            deficit=deficit,
                        )
                    )

    hints.sort(key=lambda h: (-h.deficit, h.date, h.area))
    return hints[:top_n]


def compute_vacation_concentration_hints(
    calendar_days: tuple[CalendarDay, ...],
    vacations: tuple[DateVacation, ...],
    top_n: int = 5,
) -> list[VacationConcentrationHint]:
    """日付単位休暇（`vacations`）が集中している日の上位を返す。"""
    weekday_by_date = {day.date: day.weekday for day in calendar_days}
    counts: dict[str, int] = {}
    for vacation in vacations:
        if vacation.date in weekday_by_date:
            counts[vacation.date] = counts.get(vacation.date, 0) + 1

    hints = [
        VacationConcentrationHint(
            date=date_str, weekday=weekday_by_date[date_str], vacation_count=count
        )
        for date_str, count in counts.items()
        if count > 0
    ]
    hints.sort(key=lambda h: (-h.vacation_count, h.date))
    return hints[:top_n]
