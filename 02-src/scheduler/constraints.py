"""ハード制約（HC）の定義。OR-Tools CP-SAT の変数と制約式を構築する。

実装済みのハード制約:
    HC-001: 各エリア・各時間帯の必要人数を満たす
    HC-002: スタッフが同時に複数エリアへ配置されない
    HC-003: 勤務時間制約（拘束9h・休憩1h・実働8h・週勤務日数上限）
    HC-004: 休暇・休日の制約（設定で指定）
    HC-007: 出勤(works=1)日には最低1つの配置(assign)を伴うこと（空出勤の防止）

オプション制約:
    HC-006 厳格形・同時複数名休憩の一律禁止（options.strict_single_break、初期 OFF）

SC-003（週 40 時間上限）は CP-SAT のハード制約としては実装しない。
`scheduler.result.validate_hard_constraints` による警告表示のみで扱う
（P7-7 確定判断。`01-docs/spec/CONSTRAINTS.md` 3 章参照）。

週次モデル（曜日キー・build_model）と月次モデル（日付キー・build_monthly_model）は
`DayContext`（日識別子の抽象）を介して制約構築コードを共通化する
（`internal/engine-design.md` 6 章）。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date

from ortools.sat.python import cp_model

from .calendar import CalendarDay, DateVacation
from .config_loader import AM_PM_BOUNDARY_MINUTES, Config, ShiftPattern, Staff


@dataclass(frozen=True)
class DayContext:
    """制約構築が扱う「日」の抽象。週次では曜日、月次では日付をキーに持つ。"""

    key: str  # 変数キーに使う日識別子（週次: 曜日名 / 月次: "YYYY-MM-DD"）
    weekday: str  # areas.requirements（曜日別必要人数）の参照キー
    day_type: str  # 上書き適用後の実効日種別（勤務パターン選択に使用）
    week_key: str  # 週単位制約（勤務日数上限・週労働時間）のグルーピングキー


@dataclass
class ShiftModel:
    """CP-SAT モデルと決定変数の束。"""

    config: Config
    days: tuple[DayContext, ...] = ()
    vacation_kind: Callable[[Staff, DayContext], str | None] = field(
        default=lambda staff, day: None
    )
    model: cp_model.CpModel = field(default_factory=cp_model.CpModel)
    # works[(staff名, 日キー, パターン名)] = そのパターンで勤務するか
    works: dict[tuple[str, str, str], cp_model.IntVar] = field(default_factory=dict)
    # assign[(staff名, 日キー, エリア名, スロット開始分)] = そのスロットで配置されるか
    assign: dict[tuple[str, str, str, int], cp_model.IntVar] = field(
        default_factory=dict
    )
    # break_start[(staff名, 日キー, スロット開始分)] = そのスロットから休憩を開始するか
    break_start: dict[tuple[str, str, int], cp_model.IntVar] = field(
        default_factory=dict
    )
    # 日キー -> その日のスロット開始分のリスト
    slots: dict[str, list[int]] = field(default_factory=dict)


def patterns_for_day(config: Config, day: DayContext) -> tuple[ShiftPattern, ...]:
    """日の実効日種別（day_type）から選択可能な勤務パターンを返す。"""
    return tuple(p for p in config.shift_patterns if day.day_type in p.day_types)


def _weekly_day_contexts(config: Config) -> tuple[DayContext, ...]:
    return tuple(
        DayContext(
            key=weekday,
            weekday=weekday,
            day_type=config.day_types[weekday],
            week_key="week",
        )
        for weekday in config.open_weekdays()
    )


def _weekly_vacation_kind(staff: Staff, day: DayContext) -> str | None:
    vacation = staff.vacation_on(day.weekday)
    return vacation.kind if vacation else None


def _iso_week_key(date_str: str) -> str:
    year, week, _ = date.fromisoformat(date_str).isocalendar()
    return f"{year}-W{week:02d}"


def _monthly_day_contexts(calendar_days: Sequence[CalendarDay]) -> tuple[DayContext, ...]:
    return tuple(
        DayContext(
            key=day.date,
            weekday=day.weekday,
            day_type=day.day_type,
            week_key=_iso_week_key(day.date),
        )
        for day in calendar_days
    )


def _monthly_vacation_kind(
    date_vacations: Sequence[DateVacation],
) -> Callable[[Staff, DayContext], str | None]:
    lookup = {(v.staff, v.date): v.kind for v in date_vacations}

    def vacation_kind(staff: Staff, day: DayContext) -> str | None:
        return lookup.get((staff.name, day.key))

    return vacation_kind


def _days_by_week(days: Sequence[DayContext]) -> dict[str, tuple[DayContext, ...]]:
    groups: dict[str, list[DayContext]] = {}
    for day in days:
        groups.setdefault(day.week_key, []).append(day)
    return {key: tuple(value) for key, value in groups.items()}


def build_model(config: Config) -> ShiftModel:
    """設定から 1 週間分のシフトモデル（変数 + 全ハード制約）を構築する。"""
    return _build(config, _weekly_day_contexts(config), _weekly_vacation_kind)


def build_monthly_model(
    config: Config,
    calendar_days: Sequence[CalendarDay],
    date_vacations: Sequence[DateVacation],
) -> ShiftModel:
    """対象月のカレンダー展開結果から月次シフトモデルを構築する（P6-3）。"""
    days = _monthly_day_contexts(calendar_days)
    vacation_kind = _monthly_vacation_kind(date_vacations)
    return _build(config, days, vacation_kind)


def _build(
    config: Config,
    days: tuple[DayContext, ...],
    vacation_kind: Callable[[Staff, DayContext], str | None],
) -> ShiftModel:
    sm = ShiftModel(config=config, days=days, vacation_kind=vacation_kind)
    _create_variables(sm)
    add_hc001_area_headcount(sm)
    add_hc002_single_assignment(sm)
    add_hc003_work_pattern(sm)
    add_hc004_vacations(sm)
    add_hc007_no_empty_attendance(sm)
    add_optional_strict_single_break(sm)
    return sm


def _day_slots(config: Config, day: DayContext) -> list[int]:
    """勤務パターンと必要人数の範囲を覆うスロット列を返す。"""
    patterns = patterns_for_day(config, day)
    starts = [p.window.start for p in patterns]
    ends = [p.window.end for p in patterns]
    for area in config.areas:
        for band in area.requirements[day.weekday]:
            starts.append(band.window.start)
            ends.append(band.window.end)
    if not starts:
        return []
    step = config.slot_minutes
    return list(range(min(starts), max(ends), step))


def _vacation_blocks(kind: str | None, slot: int, slot_minutes: int) -> bool:
    """HC-004: 休暇によりそのスロットが勤務不可かどうか。"""
    if kind is None:
        return False
    if kind == "full":
        return True
    if kind == "am":
        return slot < AM_PM_BOUNDARY_MINUTES
    return slot + slot_minutes > AM_PM_BOUNDARY_MINUTES  # pm


def _create_variables(sm: ShiftModel) -> None:
    config = sm.config
    for day in sm.days:
        slots = _day_slots(config, day)
        sm.slots[day.key] = slots
        patterns = patterns_for_day(config, day)
        for staff in config.staff:
            for pattern in patterns:
                sm.works[(staff.name, day.key, pattern.name)] = sm.model.new_bool_var(
                    f"works_{staff.name}_{day.key}_{pattern.name}"
                )
            for area in config.areas:
                if not staff.qualifies(area):
                    continue
                for slot in slots:
                    # いずれかのパターンの勤務時間内のスロットのみ変数を作る
                    if not any(p.window.contains(slot) for p in patterns):
                        continue
                    sm.assign[(staff.name, day.key, area.name, slot)] = (
                        sm.model.new_bool_var(
                            f"assign_{staff.name}_{day.key}_{area.name}_{slot}"
                        )
                    )


def add_hc001_area_headcount(sm: ShiftModel) -> None:
    """HC-001: 各エリア・各時間帯の必要人数を満たす。"""
    config = sm.config
    for day in sm.days:
        for area in config.areas:
            for band in area.requirements[day.weekday]:
                for slot in sm.slots[day.key]:
                    if not band.window.contains(slot):
                        continue
                    members = [
                        sm.assign[(staff.name, day.key, area.name, slot)]
                        for staff in config.staff
                        if (staff.name, day.key, area.name, slot) in sm.assign
                    ]
                    sm.model.add(sum(members) >= band.headcount)


def add_hc002_single_assignment(sm: ShiftModel) -> None:
    """HC-002: 同一時刻に複数エリアへ配置されない。"""
    config = sm.config
    for day in sm.days:
        for staff in config.staff:
            for slot in sm.slots[day.key]:
                cells = [
                    sm.assign[(staff.name, day.key, area.name, slot)]
                    for area in config.areas
                    if (staff.name, day.key, area.name, slot) in sm.assign
                ]
                if len(cells) > 1:
                    sm.model.add_at_most_one(cells)


def add_hc003_work_pattern(sm: ShiftModel) -> None:
    """HC-003: 勤務時間制約。

    - 1 日に選択できる勤務パターンは高々 1 つ
    - 配置は選択したパターンの勤務時間内のみ
    - 実働時間はパターンの実働（拘束 - 休憩）以内
    - 休憩ありパターンでは break_window 内に連続した休憩を 1 回取得し、
      休憩中は配置されない
    - 週（暦週。月次は部分週もそのまま適用）の勤務日数は weekly_workdays 以内
    """
    config = sm.config
    step = config.slot_minutes
    break_slots = config.work_rules.break_minutes // step
    window = config.work_rules.break_window

    for staff in config.staff:
        for day in sm.days:
            patterns = patterns_for_day(config, day)
            day_works = [sm.works[(staff.name, day.key, p.name)] for p in patterns]
            if day_works:
                sm.model.add_at_most_one(day_works)

            # 配置はパターン時間内のみ・実働時間以内
            for slot in sm.slots[day.key]:
                covering = [
                    sm.works[(staff.name, day.key, p.name)]
                    for p in patterns
                    if p.window.contains(slot)
                ]
                cells = [
                    sm.assign[(staff.name, day.key, area.name, slot)]
                    for area in config.areas
                    if (staff.name, day.key, area.name, slot) in sm.assign
                ]
                for cell in cells:
                    sm.model.add(cell <= sum(covering))

            day_cells = [
                var
                for (name, key, _, _), var in sm.assign.items()
                if name == staff.name and key == day.key
            ]
            capacity = sum(
                sm.works[(staff.name, day.key, p.name)] * (p.working_minutes // step)
                for p in patterns
            )
            if day_cells:
                sm.model.add(sum(day_cells) <= capacity)

            _add_break_constraints(sm, staff, day, patterns, break_slots, window.start, window.end)

        # 週の勤務日数上限（暦週ごと。月次の部分週も按分せずそのまま適用）
        for _, days_in_week in _days_by_week(sm.days).items():
            keys_in_week = {d.key for d in days_in_week}
            week_works = [
                var
                for (name, key, _), var in sm.works.items()
                if name == staff.name and key in keys_in_week
            ]
            if week_works:
                sm.model.add(sum(week_works) <= staff.weekly_workdays)


def _add_break_constraints(
    sm: ShiftModel,
    staff: Staff,
    day: DayContext,
    patterns: tuple[ShiftPattern, ...],
    break_slots: int,
    window_start: int,
    window_end: int,
) -> None:
    """休憩ありパターン勤務時、break_window 内で連続休憩を 1 回確保する。"""
    config = sm.config
    step = config.slot_minutes
    break_patterns = [p for p in patterns if p.break_minutes > 0]
    if not break_patterns or break_slots <= 0:
        return

    candidates = []
    for slot in sm.slots[day.key]:
        break_end = slot + break_slots * step
        if slot < window_start or break_end > window_end:
            continue
        var = sm.model.new_bool_var(f"break_{staff.name}_{day.key}_{slot}")
        sm.break_start[(staff.name, day.key, slot)] = var
        candidates.append((slot, var))
        # 休憩はそのパターンの勤務時間内に収まること
        containing = [
            sm.works[(staff.name, day.key, p.name)]
            for p in break_patterns
            if p.window.contains(slot) and p.window.contains(break_end - step)
        ]
        sm.model.add(var <= sum(containing))
        # 休憩中は配置されない
        for offset in range(break_slots):
            for area in config.areas:
                key = (staff.name, day.key, area.name, slot + offset * step)
                if key in sm.assign:
                    sm.model.add(sm.assign[key] + var <= 1)

    works_with_break = sum(
        sm.works[(staff.name, day.key, p.name)] for p in break_patterns
    )
    sm.model.add(sum(var for _, var in candidates) == works_with_break)


def add_hc004_vacations(sm: ShiftModel) -> None:
    """HC-004: 休暇・休日の制約。休暇スロットへの配置と終日休暇日の勤務を禁止する。"""
    config = sm.config
    for staff in config.staff:
        for day in sm.days:
            kind = sm.vacation_kind(staff, day)
            if kind is None:
                continue
            if kind == "full":
                for pattern in patterns_for_day(config, day):
                    sm.model.add(sm.works[(staff.name, day.key, pattern.name)] == 0)
            for slot in sm.slots[day.key]:
                if not _vacation_blocks(kind, slot, config.slot_minutes):
                    continue
                for area in config.areas:
                    key = (staff.name, day.key, area.name, slot)
                    if key in sm.assign:
                        sm.model.add(sm.assign[key] == 0)


def add_hc007_no_empty_attendance(sm: ShiftModel) -> None:
    """HC-007: 出勤(works=1)日には最低1つの配置(assign)を伴うこと（空出勤の防止）。

    works自体にコストがかからず、SC-004（勤務回数均等化）等のworks基準の
    均等化圧力が働く場合、配置を一切伴わない出勤（works=1, assign=0）を
    追加するだけで目的関数を改善できてしまう縮退解が最適とみなされうる
    （P6-6で観測。詳細は `internal/engine-design.md` 3章の注記を参照）。
    各（staff, 日）について「その日のworks合計 ≤ その日のassign合計」を
    課し、この状態を構造的に禁止する。週次・月次共通のDayContext抽象で
    動作する。
    """
    for staff in sm.config.staff:
        for day in sm.days:
            patterns = patterns_for_day(sm.config, day)
            day_works = sum(
                sm.works[(staff.name, day.key, p.name)] for p in patterns
            )
            day_assign = sum(
                var
                for (name, key, _, _), var in sm.assign.items()
                if name == staff.name and key == day.key
            )
            sm.model.add(day_works <= day_assign)


def add_optional_strict_single_break(sm: ShiftModel) -> None:
    """オプション: HC-006 厳格形（options.strict_single_break.enabled、初期 OFF）。

    基本形（窓口人数維持）は HC-001 × HC-003(d) の組み合わせで充足済みのため、
    このオプションは「同時に複数名が休憩に入ることの一律禁止」のみを追加する。
    各（日, スロット）について、そのスロットを覆う休憩を開始しているスタッフの
    合計人数が高々 1 人であることを課す:
    各（日, スロット）: Σ_staff Σ_{開始が当該スロットを覆う} break_start ≤ 1
    """
    config = sm.config
    if not config.strict_single_break.enabled:
        return
    step = config.slot_minutes
    break_slots = config.work_rules.break_minutes // step
    if break_slots <= 0:
        return

    starts_by_day: dict[str, list[tuple[int, cp_model.IntVar]]] = {}
    for (_, day_key, start_slot), var in sm.break_start.items():
        starts_by_day.setdefault(day_key, []).append((start_slot, var))

    for day in sm.days:
        starts = starts_by_day.get(day.key, [])
        for slot in sm.slots[day.key]:
            covering = [
                var
                for start_slot, var in starts
                if start_slot <= slot < start_slot + break_slots * step
            ]
            if len(covering) > 1:
                sm.model.add_at_most_one(covering)
