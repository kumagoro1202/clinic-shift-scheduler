"""YAML 設定ファイルを読み込み、スケジューラ用の設定オブジェクトへ変換する。

スキーマ定義は config/schema_reference.md を参照。
診療所固有の値はすべて設定ファイル側に置く（ハードコード禁止方針）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DAY_TYPES = ("full", "short", "half", "closed")
VACATION_KINDS = ("full", "am", "pm")
SUPPORTED_SCHEMA_VERSION = 1

# 午前休/午後休の境界（法令等に由来しない内部規約値。必要になれば設定化する）
AM_PM_BOUNDARY_MINUTES = 13 * 60


class ConfigError(ValueError):
    """設定ファイルの内容が不正な場合に送出する。"""


def parse_time(value: object) -> int:
    """"HH:MM" 形式の文字列を 0 時からの経過分へ変換する。"""
    try:
        hh, mm = str(value).split(":")
        minutes = int(hh) * 60 + int(mm)
    except ValueError as exc:
        raise ConfigError(f"時刻の形式が不正です: {value!r}") from exc
    if not 0 <= minutes < 24 * 60:
        raise ConfigError(f"時刻が範囲外です: {value!r}")
    return minutes


def format_time(minutes: int) -> str:
    """0 時からの経過分を "HH:MM" 形式へ変換する。"""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


@dataclass(frozen=True)
class TimeRange:
    start: int  # 0時からの経過分
    end: int

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise ConfigError(
                f"時間帯の開始が終了以降になっています: "
                f"{format_time(self.start)}-{format_time(self.end)}"
            )

    def contains(self, minute: int) -> bool:
        return self.start <= minute < self.end


@dataclass(frozen=True)
class WorkRules:
    binding_hours: int
    break_minutes: int
    working_hours: int
    break_window: TimeRange


@dataclass(frozen=True)
class WeeklyHoursCheck:
    enabled: bool
    limit_hours: int


@dataclass(frozen=True)
class ShiftPattern:
    name: str
    day_types: tuple[str, ...]
    window: TimeRange
    break_minutes: int

    @property
    def working_minutes(self) -> int:
        return self.window.end - self.window.start - self.break_minutes


@dataclass(frozen=True)
class RequirementBand:
    window: TimeRange
    headcount: int


@dataclass(frozen=True)
class Area:
    name: str
    required_skills: tuple[str, ...]
    requirements: dict[str, tuple[RequirementBand, ...]]  # weekday -> bands


@dataclass(frozen=True)
class Vacation:
    weekday: str
    kind: str  # full / am / pm


@dataclass(frozen=True)
class Staff:
    name: str
    employment: str
    weekly_workdays: int
    skills: dict[str, int]
    vacations: tuple[Vacation, ...]

    def qualifies(self, area: Area) -> bool:
        """エリアの必要スキルのいずれかを 1 以上持っていれば配置可能。"""
        return any(self.skills.get(key, 0) > 0 for key in area.required_skills)

    def vacation_on(self, weekday: str) -> Vacation | None:
        for vacation in self.vacations:
            if vacation.weekday == weekday:
                return vacation
        return None


@dataclass(frozen=True)
class Config:
    work_rules: WorkRules
    weekly_hours_check: WeeklyHoursCheck
    slot_minutes: int
    day_types: dict[str, str]  # weekday -> day_type
    clinic_hours: dict[str, dict[str, TimeRange | None]]
    shift_patterns: tuple[ShiftPattern, ...]
    areas: tuple[Area, ...]
    staff: tuple[Staff, ...]

    def patterns_for(self, weekday: str) -> tuple[ShiftPattern, ...]:
        day_type = self.day_types[weekday]
        return tuple(p for p in self.shift_patterns if day_type in p.day_types)

    def open_weekdays(self) -> tuple[str, ...]:
        return tuple(d for d in WEEKDAYS if self.day_types[d] != "closed")


def _require(mapping: dict, key: str, context: str) -> object:
    if not isinstance(mapping, dict) or key not in mapping:
        raise ConfigError(f"{context} に必須キー {key!r} がありません")
    return mapping[key]


def _check_slot_aligned(minutes: int, slot_minutes: int, context: str) -> None:
    if minutes % slot_minutes != 0:
        raise ConfigError(
            f"{context} の時刻 {format_time(minutes)} が "
            f"slot_minutes({slot_minutes}分) の倍数になっていません"
        )


def _load_work_rules(raw: dict) -> WorkRules:
    window_raw = _require(raw, "break_window", "work_rules")
    rules = WorkRules(
        binding_hours=int(_require(raw, "binding_hours", "work_rules")),
        break_minutes=int(_require(raw, "break_minutes", "work_rules")),
        working_hours=int(_require(raw, "working_hours", "work_rules")),
        break_window=TimeRange(
            parse_time(_require(window_raw, "start", "break_window")),
            parse_time(_require(window_raw, "end", "break_window")),
        ),
    )
    if rules.binding_hours * 60 != rules.working_hours * 60 + rules.break_minutes:
        raise ConfigError(
            "work_rules が不整合です: 拘束時間 = 実働時間 + 休憩 になっていません"
        )
    return rules


def _load_patterns(
    raw_list: list, work_rules: WorkRules, slot_minutes: int
) -> tuple[ShiftPattern, ...]:
    patterns = []
    for raw in raw_list:
        name = str(_require(raw, "name", "shift_patterns"))
        day_types = tuple(str(t) for t in _require(raw, "day_types", name))
        for day_type in day_types:
            if day_type not in DAY_TYPES:
                raise ConfigError(f"パターン {name} の day_type が不正です: {day_type}")
        window = TimeRange(
            parse_time(_require(raw, "start", name)),
            parse_time(_require(raw, "end", name)),
        )
        break_minutes = int(_require(raw, "break_minutes", name))
        _check_slot_aligned(window.start, slot_minutes, f"パターン {name}")
        _check_slot_aligned(window.end, slot_minutes, f"パターン {name}")
        if break_minutes > 0:
            binding = window.end - window.start
            if binding != work_rules.binding_hours * 60:
                raise ConfigError(
                    f"パターン {name} の拘束時間が work_rules.binding_hours "
                    f"({work_rules.binding_hours}時間) と一致しません"
                )
            if break_minutes != work_rules.break_minutes:
                raise ConfigError(
                    f"パターン {name} の休憩が work_rules.break_minutes "
                    f"({work_rules.break_minutes}分) と一致しません"
                )
        patterns.append(ShiftPattern(name, day_types, window, break_minutes))
    if len({p.name for p in patterns}) != len(patterns):
        raise ConfigError("shift_patterns の name が重複しています")
    return tuple(patterns)


def _load_areas(raw_list: list, slot_minutes: int) -> tuple[Area, ...]:
    areas = []
    for raw in raw_list:
        name = str(_require(raw, "name", "areas"))
        skills = tuple(str(s) for s in _require(raw, "required_skills", name))
        requirements: dict[str, tuple[RequirementBand, ...]] = {}
        raw_requirements = _require(raw, "requirements", name)
        for weekday in WEEKDAYS:
            bands = []
            for band_raw in raw_requirements.get(weekday, []) or []:
                window = TimeRange(
                    parse_time(_require(band_raw, "start", f"{name}.{weekday}")),
                    parse_time(_require(band_raw, "end", f"{name}.{weekday}")),
                )
                headcount = int(_require(band_raw, "headcount", f"{name}.{weekday}"))
                if headcount < 0:
                    raise ConfigError(f"{name}.{weekday} の headcount が負です")
                _check_slot_aligned(window.start, slot_minutes, f"{name}.{weekday}")
                _check_slot_aligned(window.end, slot_minutes, f"{name}.{weekday}")
                bands.append(RequirementBand(window, headcount))
            requirements[weekday] = tuple(bands)
        areas.append(Area(name, skills, requirements))
    if len({a.name for a in areas}) != len(areas):
        raise ConfigError("areas の name が重複しています")
    return tuple(areas)


def _load_staff(raw_list: list) -> tuple[Staff, ...]:
    members = []
    for raw in raw_list:
        name = str(_require(raw, "name", "staff"))
        skills_raw = _require(raw, "skills", name)
        skills = {str(k): int(v) for k, v in skills_raw.items()}
        for key, score in skills.items():
            if not 0 <= score <= 100:
                raise ConfigError(f"{name} のスキル {key} が 0〜100 の範囲外です")
        vacations = []
        for vacation_raw in raw.get("vacations", []) or []:
            weekday = str(_require(vacation_raw, "weekday", f"{name}.vacations"))
            kind = str(_require(vacation_raw, "kind", f"{name}.vacations"))
            if weekday not in WEEKDAYS:
                raise ConfigError(f"{name} の休暇の weekday が不正です: {weekday}")
            if kind not in VACATION_KINDS:
                raise ConfigError(f"{name} の休暇の kind が不正です: {kind}")
            vacations.append(Vacation(weekday, kind))
        members.append(
            Staff(
                name=name,
                employment=str(_require(raw, "employment", name)),
                weekly_workdays=int(_require(raw, "weekly_workdays", name)),
                skills=skills,
                vacations=tuple(vacations),
            )
        )
    if len({m.name for m in members}) != len(members):
        raise ConfigError("staff の name が重複しています")
    return tuple(members)


def _load_clinic_hours(raw: dict) -> dict[str, dict[str, TimeRange | None]]:
    hours: dict[str, dict[str, TimeRange | None]] = {}
    for weekday in WEEKDAYS:
        day_raw = raw.get(weekday) or {}
        day_hours: dict[str, TimeRange | None] = {}
        for half in ("am", "pm"):
            value = day_raw.get(half)
            day_hours[half] = (
                TimeRange(parse_time(value[0]), parse_time(value[1])) if value else None
            )
        hours[weekday] = day_hours
    return hours


def load_config(path: str | Path) -> Config:
    """YAML 設定ファイルを読み込み、検証済みの Config を返す。"""
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"設定ファイルが見つかりません: {path}")
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ConfigError("設定ファイルのトップレベルはマッピングである必要があります")

    version = raw.get("schema_version")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise ConfigError(
            f"schema_version {version!r} は未対応です"
            f"（対応バージョン: {SUPPORTED_SCHEMA_VERSION}）"
        )

    slot_minutes = int(_require(raw, "slot_minutes", "設定"))
    if slot_minutes <= 0 or 60 % slot_minutes != 0:
        raise ConfigError("slot_minutes は 60 の約数の正整数を指定してください")

    day_types_raw = _require(raw, "day_types", "設定")
    day_types = {}
    for weekday in WEEKDAYS:
        day_type = str(_require(day_types_raw, weekday, "day_types"))
        if day_type not in DAY_TYPES:
            raise ConfigError(f"day_types.{weekday} が不正です: {day_type}")
        day_types[weekday] = day_type

    work_rules = _load_work_rules(_require(raw, "work_rules", "設定"))
    options_raw = raw.get("options", {}) or {}
    weekly_raw = options_raw.get("weekly_hours_check", {}) or {}
    weekly_hours_check = WeeklyHoursCheck(
        enabled=bool(weekly_raw.get("enabled", False)),
        limit_hours=int(weekly_raw.get("limit_hours", 40)),
    )

    patterns = _load_patterns(
        _require(raw, "shift_patterns", "設定"), work_rules, slot_minutes
    )
    areas = _load_areas(_require(raw, "areas", "設定"), slot_minutes)
    staff = _load_staff(_require(raw, "staff", "設定"))

    config = Config(
        work_rules=work_rules,
        weekly_hours_check=weekly_hours_check,
        slot_minutes=slot_minutes,
        day_types=day_types,
        clinic_hours=_load_clinic_hours(raw.get("clinic_hours", {}) or {}),
        shift_patterns=patterns,
        areas=areas,
        staff=staff,
    )
    _validate_cross_references(config)
    return config


def _validate_cross_references(config: Config) -> None:
    """設定間の整合性を検証する。"""
    for weekday in config.open_weekdays():
        has_requirement = any(
            area.requirements[weekday] for area in config.areas
        )
        if has_requirement and not config.patterns_for(weekday):
            raise ConfigError(
                f"{weekday} に必要人数があるのに選択可能な勤務パターンがありません"
            )
    for area in config.areas:
        qualified = [s for s in config.staff if s.qualifies(area)]
        if not qualified and any(area.requirements[d] for d in WEEKDAYS):
            raise ConfigError(
                f"エリア {area.name} に配置可能なスタッフが 1 人もいません"
            )
