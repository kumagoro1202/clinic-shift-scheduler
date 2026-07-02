"""ハード制約（HC）の定義。OR-Tools CP-SAT の変数と制約式を構築する。

実装済みのハード制約:
    HC-001: 各エリア・各時間帯の必要人数を満たす
    HC-002: スタッフが同時に複数エリアへ配置されない
    HC-003: 勤務時間制約（拘束9h・休憩1h・実働8h・週勤務日数上限）
    HC-004: 休暇・休日の制約（設定で指定）

オプション制約:
    週労働時間チェック（options.weekly_hours_check、初期 OFF）
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from .config_loader import AM_PM_BOUNDARY_MINUTES, Config, ShiftPattern, Staff


@dataclass
class ShiftModel:
    """CP-SAT モデルと決定変数の束。"""

    config: Config
    model: cp_model.CpModel = field(default_factory=cp_model.CpModel)
    # works[(staff名, weekday, パターン名)] = そのパターンで勤務するか
    works: dict[tuple[str, str, str], cp_model.IntVar] = field(default_factory=dict)
    # assign[(staff名, weekday, エリア名, スロット開始分)] = そのスロットで配置されるか
    assign: dict[tuple[str, str, str, int], cp_model.IntVar] = field(
        default_factory=dict
    )
    # break_start[(staff名, weekday, スロット開始分)] = そのスロットから休憩を開始するか
    break_start: dict[tuple[str, str, int], cp_model.IntVar] = field(
        default_factory=dict
    )
    # weekday -> その日のスロット開始分のリスト
    slots: dict[str, list[int]] = field(default_factory=dict)


def _day_slots(config: Config, weekday: str) -> list[int]:
    """勤務パターンと必要人数の範囲を覆うスロット列を返す。"""
    starts = [p.window.start for p in config.patterns_for(weekday)]
    ends = [p.window.end for p in config.patterns_for(weekday)]
    for area in config.areas:
        for band in area.requirements[weekday]:
            starts.append(band.window.start)
            ends.append(band.window.end)
    if not starts:
        return []
    step = config.slot_minutes
    return list(range(min(starts), max(ends), step))


def _vacation_blocks(staff: Staff, weekday: str, slot: int, slot_minutes: int) -> bool:
    """HC-004: 休暇によりそのスロットが勤務不可かどうか。"""
    vacation = staff.vacation_on(weekday)
    if vacation is None:
        return False
    if vacation.kind == "full":
        return True
    if vacation.kind == "am":
        return slot < AM_PM_BOUNDARY_MINUTES
    return slot + slot_minutes > AM_PM_BOUNDARY_MINUTES  # pm


def build_model(config: Config) -> ShiftModel:
    """設定から 1 週間分のシフトモデル（変数 + 全ハード制約）を構築する。"""
    sm = ShiftModel(config=config)
    _create_variables(sm)
    add_hc001_area_headcount(sm)
    add_hc002_single_assignment(sm)
    add_hc003_work_pattern(sm)
    add_hc004_vacations(sm)
    add_optional_weekly_hours_check(sm)
    return sm


def _create_variables(sm: ShiftModel) -> None:
    config = sm.config
    for weekday in config.open_weekdays():
        slots = _day_slots(config, weekday)
        sm.slots[weekday] = slots
        patterns = config.patterns_for(weekday)
        for staff in config.staff:
            for pattern in patterns:
                sm.works[(staff.name, weekday, pattern.name)] = sm.model.new_bool_var(
                    f"works_{staff.name}_{weekday}_{pattern.name}"
                )
            for area in config.areas:
                if not staff.qualifies(area):
                    continue
                for slot in slots:
                    # いずれかのパターンの勤務時間内のスロットのみ変数を作る
                    if not any(p.window.contains(slot) for p in patterns):
                        continue
                    sm.assign[(staff.name, weekday, area.name, slot)] = (
                        sm.model.new_bool_var(
                            f"assign_{staff.name}_{weekday}_{area.name}_{slot}"
                        )
                    )


def add_hc001_area_headcount(sm: ShiftModel) -> None:
    """HC-001: 各エリア・各時間帯の必要人数を満たす。"""
    config = sm.config
    for weekday in config.open_weekdays():
        for area in config.areas:
            for band in area.requirements[weekday]:
                for slot in sm.slots[weekday]:
                    if not band.window.contains(slot):
                        continue
                    members = [
                        sm.assign[(staff.name, weekday, area.name, slot)]
                        for staff in config.staff
                        if (staff.name, weekday, area.name, slot) in sm.assign
                    ]
                    sm.model.add(sum(members) >= band.headcount)


def add_hc002_single_assignment(sm: ShiftModel) -> None:
    """HC-002: 同一時刻に複数エリアへ配置されない。"""
    config = sm.config
    for weekday in config.open_weekdays():
        for staff in config.staff:
            for slot in sm.slots[weekday]:
                cells = [
                    sm.assign[(staff.name, weekday, area.name, slot)]
                    for area in config.areas
                    if (staff.name, weekday, area.name, slot) in sm.assign
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
    - 週の勤務日数は weekly_workdays 以内
    """
    config = sm.config
    step = config.slot_minutes
    break_slots = config.work_rules.break_minutes // step
    window = config.work_rules.break_window

    for staff in config.staff:
        for weekday in config.open_weekdays():
            patterns = config.patterns_for(weekday)
            day_works = [sm.works[(staff.name, weekday, p.name)] for p in patterns]
            if day_works:
                sm.model.add_at_most_one(day_works)

            # 配置はパターン時間内のみ・実働時間以内
            for slot in sm.slots[weekday]:
                covering = [
                    sm.works[(staff.name, weekday, p.name)]
                    for p in patterns
                    if p.window.contains(slot)
                ]
                cells = [
                    sm.assign[(staff.name, weekday, area.name, slot)]
                    for area in config.areas
                    if (staff.name, weekday, area.name, slot) in sm.assign
                ]
                for cell in cells:
                    sm.model.add(cell <= sum(covering))

            day_cells = [
                var
                for (name, day, _, _), var in sm.assign.items()
                if name == staff.name and day == weekday
            ]
            capacity = sum(
                sm.works[(staff.name, weekday, p.name)] * (p.working_minutes // step)
                for p in patterns
            )
            if day_cells:
                sm.model.add(sum(day_cells) <= capacity)

            _add_break_constraints(
                sm, staff, weekday, patterns, break_slots, window.start, window.end
            )

        # 週の勤務日数上限
        week_works = [
            var for (name, _, _), var in sm.works.items() if name == staff.name
        ]
        if week_works:
            sm.model.add(sum(week_works) <= staff.weekly_workdays)


def _add_break_constraints(
    sm: ShiftModel,
    staff: Staff,
    weekday: str,
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
    for slot in sm.slots[weekday]:
        break_end = slot + break_slots * step
        if slot < window_start or break_end > window_end:
            continue
        var = sm.model.new_bool_var(f"break_{staff.name}_{weekday}_{slot}")
        sm.break_start[(staff.name, weekday, slot)] = var
        candidates.append((slot, var))
        # 休憩はそのパターンの勤務時間内に収まること
        containing = [
            sm.works[(staff.name, weekday, p.name)]
            for p in break_patterns
            if p.window.contains(slot) and p.window.contains(break_end - step)
        ]
        sm.model.add(var <= sum(containing))
        # 休憩中は配置されない
        for offset in range(break_slots):
            for area in config.areas:
                key = (staff.name, weekday, area.name, slot + offset * step)
                if key in sm.assign:
                    sm.model.add(sm.assign[key] + var <= 1)

    works_with_break = sum(
        sm.works[(staff.name, weekday, p.name)] for p in break_patterns
    )
    sm.model.add(sum(var for _, var in candidates) == works_with_break)


def add_hc004_vacations(sm: ShiftModel) -> None:
    """HC-004: 休暇・休日の制約。休暇スロットへの配置と終日休暇日の勤務を禁止する。"""
    config = sm.config
    for staff in config.staff:
        for weekday in config.open_weekdays():
            vacation = staff.vacation_on(weekday)
            if vacation is None:
                continue
            if vacation.kind == "full":
                for pattern in config.patterns_for(weekday):
                    sm.model.add(sm.works[(staff.name, weekday, pattern.name)] == 0)
            for slot in sm.slots[weekday]:
                if not _vacation_blocks(staff, weekday, slot, config.slot_minutes):
                    continue
                for area in config.areas:
                    key = (staff.name, weekday, area.name, slot)
                    if key in sm.assign:
                        sm.model.add(sm.assign[key] == 0)


def add_optional_weekly_hours_check(sm: ShiftModel) -> None:
    """オプション: 週労働時間の上限チェック（初期 OFF）。"""
    config = sm.config
    check = config.weekly_hours_check
    if not check.enabled:
        return
    for staff in config.staff:
        total_minutes = sum(
            var * _pattern_by_name(config, pattern_name).working_minutes
            for (name, _, pattern_name), var in sm.works.items()
            if name == staff.name
        )
        sm.model.add(total_minutes <= check.limit_hours * 60)


def _pattern_by_name(config: Config, name: str) -> ShiftPattern:
    for pattern in config.shift_patterns:
        if pattern.name == name:
            return pattern
    raise KeyError(name)
