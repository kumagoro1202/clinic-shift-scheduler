"""シフト生成エンジン。設定を読み込み CP-SAT ソルバーで週次・月次のシフトを生成する。"""

from __future__ import annotations

from pathlib import Path

from ortools.sat.python import cp_model

from . import objectives
from .calendar import expand_month, load_monthly_schedule
from .config_loader import Config, format_time, load_config
from .constraints import ShiftModel, build_model, build_monthly_model, patterns_for_day

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
    return _solve(build_model(config), time_limit_seconds)


def run_from_file(config_path: str | Path, time_limit_seconds: float = 60.0) -> dict:
    """設定ファイルパスからシフトを生成する。"""
    return run(load_config(config_path), time_limit_seconds)


def run_monthly(
    config: Config,
    monthly_schedule_path: str | Path,
    time_limit_seconds: float = 60.0,
) -> dict:
    """月次入力ファイルを指定し、対象月 1 ヶ月分のシフトを生成する（P6-3）。

    Returns:
        {
            "status": "OPTIMAL" | "FEASIBLE" | "INFEASIBLE" | ...,
            "schedule": {"YYYY-MM-DD": {スタッフ名: {...}}} | None,
        }
    """
    monthly = load_monthly_schedule(monthly_schedule_path, config)
    calendar_days = expand_month(config, monthly)
    sm = build_monthly_model(config, calendar_days, monthly.vacations)
    return _solve(sm, time_limit_seconds)


def run_monthly_from_files(
    config_path: str | Path,
    monthly_schedule_path: str | Path,
    time_limit_seconds: float = 60.0,
) -> dict:
    """設定ファイル・月次入力ファイルのパスから月次シフトを生成する。"""
    return run_monthly(load_config(config_path), monthly_schedule_path, time_limit_seconds)


def _solve(sm: ShiftModel, time_limit_seconds: float) -> dict:
    _set_objective(sm)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    status = solver.solve(sm.model)
    status_name = solver.status_name(status)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": status_name, "schedule": None}
    return {"status": status_name, "schedule": _extract_schedule(sm, solver)}


def _set_objective(sm: ShiftModel) -> None:
    """必要人数を満たす範囲で、勤務日数・SC-001スキルバランス乖離・
    SC-002連続配置ブロック数・配置スロット数を最小化する
    （`internal/engine-design.md` 4.1節。SC-004/005はP6-6〜7で追加）。
    """
    sc001_penalty = objectives.add_sc001_skill_balance(sm)
    sc001_weight = objectives.weight_for(sm.config.optimization_mode, "sc001")
    sc002_penalty = objectives.add_sc002_continuous_placement(sm)
    sc002_weight = objectives.weight_for(sm.config.optimization_mode, "sc002")
    sm.model.minimize(
        _WORKDAY_WEIGHT * sum(sm.works.values())
        + sc001_weight * sc001_penalty
        + sc002_weight * sc002_penalty
        + sum(sm.assign.values())
    )


def _extract_schedule(sm: ShiftModel, solver: cp_model.CpSolver) -> dict:
    config = sm.config
    step = config.slot_minutes
    break_slots = config.work_rules.break_minutes // step
    schedule: dict[str, dict] = {}

    for day in sm.days:
        day_result: dict[str, dict] = {}
        patterns = patterns_for_day(config, day)
        for staff in config.staff:
            pattern_name = None
            for pattern in patterns:
                if solver.value(sm.works[(staff.name, day.key, pattern.name)]):
                    pattern_name = pattern.name
                    break
            if pattern_name is None:
                continue

            segments = []
            for area in config.areas:
                assigned = [
                    slot
                    for slot in sm.slots[day.key]
                    if (staff.name, day.key, area.name, slot) in sm.assign
                    and solver.value(sm.assign[(staff.name, day.key, area.name, slot)])
                ]
                segments.extend(_merge_slots(assigned, step, area.name))
            segments.sort(key=lambda seg: seg["start"])

            break_range = None
            for (name, key, slot), var in sm.break_start.items():
                if name == staff.name and key == day.key and solver.value(var):
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
        schedule[day.key] = day_result
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
