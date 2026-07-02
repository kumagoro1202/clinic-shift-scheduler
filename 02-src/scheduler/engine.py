"""シフト生成エンジン。設定を読み込み CP-SAT ソルバーで 1 週間分のシフトを生成する。"""

from __future__ import annotations

from pathlib import Path

from ortools.sat.python import cp_model

from .config_loader import Config, format_time, load_config
from .constraints import ShiftModel, build_model

# 勤務日数の最小化を配置スロット最小化より優先する重み
_WORKDAY_WEIGHT = 100


def run(config: Config, time_limit_seconds: float = 60.0) -> dict:
    """1 週間分のシフトを生成して返す。

    Returns:
        {
            "status": "OPTIMAL" | "FEASIBLE" | "INFEASIBLE" | ...,
            "schedule": {weekday: {スタッフ名: {...}}} | None,
        }
    """
    sm = build_model(config)
    _set_objective(sm)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    status = solver.solve(sm.model)
    status_name = solver.status_name(status)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": status_name, "schedule": None}
    return {"status": status_name, "schedule": _extract_schedule(sm, solver)}


def run_from_file(config_path: str | Path, time_limit_seconds: float = 60.0) -> dict:
    """設定ファイルパスからシフトを生成する。"""
    return run(load_config(config_path), time_limit_seconds)


def _set_objective(sm: ShiftModel) -> None:
    """必要人数を満たす範囲で、勤務日数と配置スロット数を最小化する。"""
    sm.model.minimize(
        _WORKDAY_WEIGHT * sum(sm.works.values()) + sum(sm.assign.values())
    )


def _extract_schedule(sm: ShiftModel, solver: cp_model.CpSolver) -> dict:
    config = sm.config
    step = config.slot_minutes
    break_slots = config.work_rules.break_minutes // step
    schedule: dict[str, dict] = {}

    for weekday in config.open_weekdays():
        day_result: dict[str, dict] = {}
        for staff in config.staff:
            pattern_name = None
            for pattern in config.patterns_for(weekday):
                if solver.value(sm.works[(staff.name, weekday, pattern.name)]):
                    pattern_name = pattern.name
                    break
            if pattern_name is None:
                continue

            segments = []
            for area in config.areas:
                assigned = [
                    slot
                    for slot in sm.slots[weekday]
                    if (staff.name, weekday, area.name, slot) in sm.assign
                    and solver.value(sm.assign[(staff.name, weekday, area.name, slot)])
                ]
                segments.extend(_merge_slots(assigned, step, area.name))
            segments.sort(key=lambda seg: seg["start"])

            break_range = None
            for (name, day, slot), var in sm.break_start.items():
                if name == staff.name and day == weekday and solver.value(var):
                    break_range = {
                        "start": format_time(slot),
                        "end": format_time(slot + break_slots * step),
                    }
                    break

            day_result[staff.name] = {
                "pattern": pattern_name,
                "work": segments,
                "break": break_range,
            }
        schedule[weekday] = day_result
    return schedule


def _merge_slots(slots: list[int], step: int, area_name: str) -> list[dict]:
    """連続するスロットをひとつの時間帯にまとめる。"""
    segments = []
    for slot in sorted(slots):
        if segments and segments[-1]["_end"] == slot:
            segments[-1]["_end"] = slot + step
        else:
            segments.append({"_start": slot, "_end": slot + step})
    return [
        {
            "area": area_name,
            "start": format_time(seg["_start"]),
            "end": format_time(seg["_end"]),
        }
        for seg in segments
    ]
