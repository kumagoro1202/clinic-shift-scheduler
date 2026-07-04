"""月次カレンダー展開（曜日テンプレート → 対象月の日付列）。

対象月の日付ごとに、曜日から基本の日種別を決め、`calendar_overrides`
（祝日・臨時休診等）で上書きする。`closed` の日は生成対象から除外する。
日付単位の休暇（`vacations`）も本モジュールで読み込み・検証する。

入力ファイル仕様は `external/input-design.md` 5 章を参照。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import yaml

from .config_loader import DAY_TYPES, Config, ConfigError, _require

SUPPORTED_MONTHLY_SCHEMA_VERSION = 2
VACATION_KINDS = ("full", "am", "pm")

# datetime.date.weekday(): Mon=0 ... Sun=6
_WEEKDAY_BY_ISO_INDEX = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


@dataclass(frozen=True)
class CalendarOverride:
    date: str  # "YYYY-MM-DD"
    day_type: str
    reason: str | None = None


@dataclass(frozen=True)
class DateVacation:
    staff: str
    date: str  # "YYYY-MM-DD"
    kind: str  # full / am / pm
    paid: bool = False


@dataclass(frozen=True)
class MonthlySchedule:
    target_month: str  # "YYYY-MM"
    calendar_overrides: tuple[CalendarOverride, ...]
    vacations: tuple[DateVacation, ...]


@dataclass(frozen=True)
class CalendarDay:
    date: str  # "YYYY-MM-DD"
    weekday: str  # 曜日別必要人数（areas.requirements）の参照キー
    day_type: str  # 上書き適用後の実効日種別（勤務パターン選択に使用）
    reason: str | None = None


def _month_dates(target_month: str) -> list[str]:
    try:
        year_str, month_str = target_month.split("-")
        year, month = int(year_str), int(month_str)
    except ValueError as exc:
        raise ConfigError(f"target_month の形式が不正です: {target_month!r}") from exc
    if not 1 <= month <= 12:
        raise ConfigError(f"target_month の月が不正です: {target_month!r}")
    first_day = date(year, month, 1)
    next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    dates = []
    current = first_day
    while current < next_month:
        dates.append(current.isoformat())
        current += timedelta(days=1)
    return dates


def load_monthly_schedule(path: str | Path, config: Config) -> MonthlySchedule:
    """月次入力ファイル（schedule-YYYYMM.yaml）を読み込み検証する。

    検証ルール V-10〜V-12（`external/input-design.md` 6 章）を適用する。
    """
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"月次設定ファイルが見つかりません: {path}")
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ConfigError("月次設定ファイルのトップレベルはマッピングである必要があります")

    version = raw.get("schema_version")
    if version != SUPPORTED_MONTHLY_SCHEMA_VERSION:
        raise ConfigError(
            f"月次設定の schema_version {version!r} は未対応です"
            f"（対応バージョン: {SUPPORTED_MONTHLY_SCHEMA_VERSION}）"
        )

    target_month = str(_require(raw, "target_month", "月次設定"))
    valid_dates = set(_month_dates(target_month))

    overrides = []
    for raw_override in raw.get("calendar_overrides", []) or []:
        override_date = str(_require(raw_override, "date", "calendar_overrides"))
        day_type = str(_require(raw_override, "day_type", "calendar_overrides"))
        if day_type not in DAY_TYPES:
            raise ConfigError(f"calendar_overrides の day_type が不正です: {day_type}")
        if override_date not in valid_dates:  # V-10
            raise ConfigError(
                f"calendar_overrides の date が対象月外です: {override_date}"
            )
        overrides.append(
            CalendarOverride(
                date=override_date,
                day_type=day_type,
                reason=raw_override.get("reason"),
            )
        )
    if len({o.date for o in overrides}) != len(overrides):
        raise ConfigError("calendar_overrides の date が重複しています")

    staff_names = {s.name for s in config.staff}
    seen_staff_dates: set[tuple[str, str]] = set()
    vacations = []
    for raw_vacation in raw.get("vacations", []) or []:
        staff_name = str(_require(raw_vacation, "staff", "vacations"))
        vacation_date = str(_require(raw_vacation, "date", "vacations"))
        kind = str(_require(raw_vacation, "kind", "vacations"))
        if staff_name not in staff_names:  # V-11
            raise ConfigError(f"vacations の staff が存在しません: {staff_name}")
        if vacation_date not in valid_dates:  # V-10
            raise ConfigError(f"vacations の date が対象月外です: {vacation_date}")
        if kind not in VACATION_KINDS:
            raise ConfigError(f"vacations の kind が不正です: {kind}")
        key = (staff_name, vacation_date)
        if key in seen_staff_dates:  # V-12
            raise ConfigError(
                f"同一スタッフ・同一日の休暇が重複しています: {staff_name} {vacation_date}"
            )
        seen_staff_dates.add(key)
        vacations.append(
            DateVacation(
                staff=staff_name,
                date=vacation_date,
                kind=kind,
                paid=bool(raw_vacation.get("paid", False)),
            )
        )

    return MonthlySchedule(
        target_month=target_month,
        calendar_overrides=tuple(overrides),
        vacations=tuple(vacations),
    )


def expand_month(config: Config, monthly: MonthlySchedule) -> tuple[CalendarDay, ...]:
    """対象月の日付列を、曜日テンプレート + カレンダー例外で展開する。

    `closed` の日（曜日由来・上書き後いずれも）は生成対象から除外する。
    """
    overrides = {o.date: o for o in monthly.calendar_overrides}
    days = []
    for date_str in _month_dates(monthly.target_month):
        weekday = _WEEKDAY_BY_ISO_INDEX[date.fromisoformat(date_str).weekday()]
        day_type = config.day_types[weekday]
        reason = None
        override = overrides.get(date_str)
        if override is not None:
            day_type = override.day_type
            reason = override.reason
        if day_type == "closed":
            continue
        days.append(
            CalendarDay(date=date_str, weekday=weekday, day_type=day_type, reason=reason)
        )
    return tuple(days)
