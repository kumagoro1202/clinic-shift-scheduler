"""P6-6 SC-004（勤務回数均等化）のテスト。

テスト専用のサンプル設定（config/samples/sample_clinic.yaml・
config/samples/sample_schedule_202608.yaml）と、本テスト専用の最小構成
設定（1エリア・2名構成・平日5日のみ・必要人数0）を使用する。実在データは
使用しない。
"""

from pathlib import Path

import pytest
from ortools.sat.python import cp_model

from scheduler import calendar, config_loader, constraints, engine, objectives

SAMPLE_CONFIG = (
    Path(__file__).resolve().parents[2] / "config" / "samples" / "sample_clinic.yaml"
)
SAMPLE_SCHEDULE = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "samples"
    / "sample_schedule_202608.yaml"
)

# 敵対的検証用の最小構成: 2名(スタッフ1・スタッフ2)、平日5日(mon〜fri)のみ営業。
# エリアの必要人数は全日0（assign変数は生成されるが充足制約は課されない）ため、
# `sm.works` を直接固定して勤務日数配分だけを自由に検証できる。
_MINIMAL_CONFIG_YAML = """
schema_version: 1
work_rules:
  binding_hours: 2
  break_minutes: 0
  working_hours: 2
  break_window: { start: "09:00", end: "09:30" }
slot_minutes: 30
day_types:
  mon: full
  tue: full
  wed: full
  thu: full
  fri: full
  sat: closed
  sun: closed
shift_patterns:
  - name: day
    day_types: [full]
    start: "09:00"
    end: "10:00"
    break_minutes: 0
areas:
  - name: area_a
    required_skills: [area_a]
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
    weekly_workdays: 7
    skills: { area_a: 50 }
    vacations: []
  - name: "スタッフ2"
    employment: full_time
    weekly_workdays: 7
    skills: { area_a: 50 }
    vacations: []
"""


@pytest.fixture(scope="module")
def sample_config():
    return config_loader.load_config(SAMPLE_CONFIG)


@pytest.fixture
def minimal_config(tmp_path):
    path = tmp_path / "minimal_clinic.yaml"
    path.write_text(_MINIMAL_CONFIG_YAML, encoding="utf-8")
    return config_loader.load_config(path)


def _all_works(sm: constraints.ShiftModel) -> list[cp_model.IntVar]:
    return [
        sm.works[(name, day.key, "day")]
        for name in ("スタッフ1", "スタッフ2")
        for day in sm.days
    ]


# --- weight_for / プリセット -----------------------------------------------


def test_weight_presets_include_sc004_matching_engine_design_table():
    """internal/engine-design.md 5章の重みプリセット表。"""
    assert objectives.weight_for("balance", "sc004") == 100
    assert objectives.weight_for("skill_focus", "sc004") == 50
    assert objectives.weight_for("days_focus", "sc004") == 300


# --- SC-004 目的関数が勤務回数均等化を誘導すること（本体） --------------------


def test_sc004_penalty_equals_forced_max_min_difference(minimal_config):
    """勤務日数配分を(スタッフ1:5日・スタッフ2:0日)に強制した場合、
    ペナルティ(max_days-min_days)が5-0=5となること。"""
    sm = constraints.build_model(minimal_config)
    penalty = objectives.add_sc004_workday_balance(sm)
    for day in sm.days:
        sm.model.add(sm.works[("スタッフ1", day.key, "day")] == 1)
        sm.model.add(sm.works[("スタッフ2", day.key, "day")] == 0)
    sm.model.minimize(penalty)

    solver = cp_model.CpSolver()
    status = solver.solve(sm.model)
    assert status == cp_model.OPTIMAL
    assert solver.value(penalty) == 5


def test_sc004_objective_prefers_balanced_split_over_skewed(minimal_config):
    """総勤務日数を5日に固定した場合、SC-004ペナルティ最小化により
    スタッフ1・スタッフ2の配分が均等(3日/2日、差1)に誘導されること
    （5日を2名で分けるとき差を最小化する唯一の分割は3/2または2/3）。"""
    sm = constraints.build_model(minimal_config)
    penalty = objectives.add_sc004_workday_balance(sm)
    sm.model.add(sum(_all_works(sm)) == 5)
    weight = objectives.weight_for(minimal_config.optimization_mode, "sc004")
    sm.model.minimize(weight * penalty)

    solver = cp_model.CpSolver()
    status = solver.solve(sm.model)
    assert status == cp_model.OPTIMAL
    assert solver.value(penalty) == 1

    staff1_total = sum(
        solver.value(sm.works[("スタッフ1", day.key, "day")]) for day in sm.days
    )
    staff2_total = sum(
        solver.value(sm.works[("スタッフ2", day.key, "day")]) for day in sm.days
    )
    assert {staff1_total, staff2_total} == {2, 3}


def test_sc004_disabled_allows_skewed_assignment_as_optimal(minimal_config):
    """敵対的検証: SC-004目的関数を無効化(=baselineのみ)すると、勤務日数の
    偏り配分(スタッフ1:5日・スタッフ2:0日)も均等配分(3日/2日)と同じ最適値として
    許容されてしまうこと。SC-004を復元(有効化)すると、同じ偏り配分の
    ペナルティ(5)が均等配分の最適値(1、上のテストで検証)より明確に
    悪化していることを確認する。"""
    total_days = 5

    # 1) baseline のみ（SC-004なし）: 自由に解かせた最適値
    sm_free = constraints.build_model(minimal_config)
    sm_free.model.add(sum(_all_works(sm_free)) == total_days)
    sm_free.model.minimize(0)
    solver_free = cp_model.CpSolver()
    status_free = solver_free.solve(sm_free.model)
    assert status_free == cp_model.OPTIMAL
    baseline_optimal = solver_free.objective_value

    # 2) baseline のみで、偏り配分(スタッフ1:5日・スタッフ2:0日)を強制
    #    -> 同じ最適値のはず（SC-004が無効な間は配分の均等性に無差別であることの確認）
    sm_forced = constraints.build_model(minimal_config)
    for day in sm_forced.days:
        sm_forced.model.add(sm_forced.works[("スタッフ1", day.key, "day")] == 1)
        sm_forced.model.add(sm_forced.works[("スタッフ2", day.key, "day")] == 0)
    sm_forced.model.minimize(0)
    solver_forced = cp_model.CpSolver()
    status_forced = solver_forced.solve(sm_forced.model)
    assert status_forced == cp_model.OPTIMAL
    assert solver_forced.objective_value == baseline_optimal, (
        "SC-004無効時は勤務日数配分に無差別のはずが、"
        "偏り配分(スタッフ1:5日・スタッフ2:0日)がbaseline最適解として"
        "許容されていません"
    )

    # 3) SC-004を復元（有効化）した上で同じ偏り配分を評価
    #    -> ペナルティ(5)が観測でき、均等配分(ペナルティ1)より
    #    悪化していることを直接確認できる
    sm_sc004_forced = constraints.build_model(minimal_config)
    penalty = objectives.add_sc004_workday_balance(sm_sc004_forced)
    for day in sm_sc004_forced.days:
        sm_sc004_forced.model.add(
            sm_sc004_forced.works[("スタッフ1", day.key, "day")] == 1
        )
        sm_sc004_forced.model.add(
            sm_sc004_forced.works[("スタッフ2", day.key, "day")] == 0
        )
    weight = objectives.weight_for(minimal_config.optimization_mode, "sc004")
    sm_sc004_forced.model.minimize(weight * penalty)
    solver_sc004_forced = cp_model.CpSolver()
    status_sc004_forced = solver_sc004_forced.solve(sm_sc004_forced.model)
    assert status_sc004_forced == cp_model.OPTIMAL
    assert solver_sc004_forced.value(penalty) == 5, (
        "偏り配分(スタッフ1:5日・スタッフ2:0日)の"
        "max_days-min_days は5のはずです"
    )
    assert solver_sc004_forced.value(penalty) > 1, (
        "SC-004有効時は偏り配分が均等配分(ペナルティ1)より悪化するはずです"
    )


# --- 月次モデルでも共通実装で動作すること（週次・月次共通コード） -------------


def test_sc004_builds_on_monthly_model_without_error(sample_config):
    """月次モデル(DayContext.key=日付)でも SC-004 が同一コードで構築できること。"""
    monthly = calendar.load_monthly_schedule(SAMPLE_SCHEDULE, sample_config)
    calendar_days = calendar.expand_month(sample_config, monthly)
    sm = constraints.build_monthly_model(sample_config, calendar_days, monthly.vacations)
    penalty = objectives.add_sc004_workday_balance(sm)
    # max_days/min_days変数を必ず生成する実装のため、生成有無はこれで判別する
    assert not isinstance(penalty, int)


def test_engine_run_monthly_with_sc004_still_feasible(sample_config):
    """SC-001・SC-002・SC-004を組み込んだ目的関数でも、月次モデルの求解が
    INFEASIBLE にならないこと（既存の月次シフト生成テストに対する回帰確認）。"""
    result = engine.run_monthly(sample_config, SAMPLE_SCHEDULE, time_limit_seconds=60.0)
    assert result["status"] in ("OPTIMAL", "FEASIBLE")
    assert result["schedule"] is not None
