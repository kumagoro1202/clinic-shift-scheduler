"""P6-7 SC-005（半日診療日の均等分散）のテスト。

テスト専用のサンプル設定（config/samples/sample_clinic.yaml・
config/samples/sample_schedule_202608.yaml）と、本テスト専用の最小構成
設定（1エリア・2名構成・full/half混在の週6営業日のみ・必要人数0）を使用する。
実在データは使用しない。
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

# 敵対的検証用の最小構成: 2名(スタッフ1・スタッフ2)。
# mon/tue/wed/fri = full（4日）、thu/sat = half（2日）、sun = closed。
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
  thu: half
  fri: full
  sat: half
  sun: closed
shift_patterns:
  - name: day
    day_types: [full]
    start: "09:00"
    end: "10:00"
    break_minutes: 0
  - name: half
    day_types: [half]
    start: "09:00"
    end: "09:30"
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
    path = tmp_path / "minimal_clinic_halfday.yaml"
    path.write_text(_MINIMAL_CONFIG_YAML, encoding="utf-8")
    return config_loader.load_config(path)


def _half_days(sm: constraints.ShiftModel):
    return [day for day in sm.days if day.day_type == "half"]


def _full_days(sm: constraints.ShiftModel):
    return [day for day in sm.days if day.day_type == "full"]


def _half_day_works(sm: constraints.ShiftModel) -> list[cp_model.IntVar]:
    return [
        sm.works[(name, day.key, "half")]
        for name in ("スタッフ1", "スタッフ2")
        for day in _half_days(sm)
    ]


# --- weight_for / プリセット -----------------------------------------------


def test_weight_presets_include_sc005_matching_engine_design_table():
    """internal/engine-design.md 5章の重みプリセット表。"""
    assert objectives.weight_for("balance", "sc005") == 50
    assert objectives.weight_for("skill_focus", "sc005") == 25
    assert objectives.weight_for("days_focus", "sc005") == 100


# --- SC-005 目的関数が半日診療日の出勤回数均等化を誘導すること（本体） ----------


def test_sc005_penalty_equals_forced_max_min_difference_on_half_days_only(
    minimal_config,
):
    """半日診療日(thu・sat)の出勤配分を(スタッフ1:2日・スタッフ2:0日)に強制した
    場合、ペナルティ(max_half_days-min_half_days)が2-0=2となること。"""
    sm = constraints.build_model(minimal_config)
    penalty = objectives.add_sc005_half_day_workday_balance(sm)
    for day in _half_days(sm):
        sm.model.add(sm.works[("スタッフ1", day.key, "half")] == 1)
        sm.model.add(sm.works[("スタッフ2", day.key, "half")] == 0)
    sm.model.minimize(penalty)

    solver = cp_model.CpSolver()
    status = solver.solve(sm.model)
    assert status == cp_model.OPTIMAL
    assert solver.value(penalty) == 2


def test_sc005_ignores_full_day_workdays(minimal_config):
    """full日(mon/tue/wed/fri)の出勤配分をスタッフ1:4日・スタッフ2:0日
    (SC-004視点では最大の偏り)に強制しても、半日診療日側の配分が均等
    (両者0日)であればSC-005ペナルティは0のままであること
    （SC-005がfull日を一切参照しないことの直接検証）。"""
    sm = constraints.build_model(minimal_config)
    penalty = objectives.add_sc005_half_day_workday_balance(sm)
    for day in _full_days(sm):
        sm.model.add(sm.works[("スタッフ1", day.key, "day")] == 1)
        sm.model.add(sm.works[("スタッフ2", day.key, "day")] == 0)
    for day in _half_days(sm):
        sm.model.add(sm.works[("スタッフ1", day.key, "half")] == 0)
        sm.model.add(sm.works[("スタッフ2", day.key, "half")] == 0)
    sm.model.minimize(penalty)

    solver = cp_model.CpSolver()
    status = solver.solve(sm.model)
    assert status == cp_model.OPTIMAL
    assert solver.value(penalty) == 0


def test_sc005_objective_prefers_balanced_split_over_skewed(minimal_config):
    """半日診療日の総出勤回数を3回に固定した場合、SC-005ペナルティ最小化により
    スタッフ1・スタッフ2の配分が(2回/1回、差1)に誘導されること
    （3回を2名の2日枠(各最大2回)で分けるとき差を最小化する分割は2/1または1/2）。"""
    sm = constraints.build_model(minimal_config)
    penalty = objectives.add_sc005_half_day_workday_balance(sm)
    sm.model.add(sum(_half_day_works(sm)) == 3)
    weight = objectives.weight_for(minimal_config.optimization_mode, "sc005")
    sm.model.minimize(weight * penalty)

    solver = cp_model.CpSolver()
    status = solver.solve(sm.model)
    assert status == cp_model.OPTIMAL
    assert solver.value(penalty) == 1

    staff1_total = sum(
        solver.value(sm.works[("スタッフ1", day.key, "half")]) for day in _half_days(sm)
    )
    staff2_total = sum(
        solver.value(sm.works[("スタッフ2", day.key, "half")]) for day in _half_days(sm)
    )
    assert {staff1_total, staff2_total} == {1, 2}


def test_sc005_disabled_allows_skewed_assignment_as_optimal(minimal_config):
    """敵対的検証: SC-005目的関数を無効化(=baselineのみ)すると、半日診療日の
    偏り配分(スタッフ1:2日・スタッフ2:0日)も均等配分と同じ最適値として
    許容されてしまうこと。SC-005を復元(有効化)すると、同じ偏り配分の
    ペナルティ(2)が観測できることを確認する。"""
    # 1) baseline のみ（SC-005なし）: 自由に解かせた最適値
    sm_free = constraints.build_model(minimal_config)
    sm_free.model.add(sum(_half_day_works(sm_free)) == 2)
    sm_free.model.minimize(0)
    solver_free = cp_model.CpSolver()
    status_free = solver_free.solve(sm_free.model)
    assert status_free == cp_model.OPTIMAL
    baseline_optimal = solver_free.objective_value

    # 2) baseline のみで、偏り配分(スタッフ1:2日・スタッフ2:0日)を強制
    #    -> 同じ最適値のはず（SC-005が無効な間は配分の均等性に無差別であることの確認）
    sm_forced = constraints.build_model(minimal_config)
    for day in _half_days(sm_forced):
        sm_forced.model.add(sm_forced.works[("スタッフ1", day.key, "half")] == 1)
        sm_forced.model.add(sm_forced.works[("スタッフ2", day.key, "half")] == 0)
    sm_forced.model.minimize(0)
    solver_forced = cp_model.CpSolver()
    status_forced = solver_forced.solve(sm_forced.model)
    assert status_forced == cp_model.OPTIMAL
    assert solver_forced.objective_value == baseline_optimal, (
        "SC-005無効時は半日診療日の出勤配分に無差別のはずが、"
        "偏り配分(スタッフ1:2日・スタッフ2:0日)がbaseline最適解として"
        "許容されていません"
    )

    # 3) SC-005を復元（有効化）した上で同じ偏り配分を評価
    #    -> ペナルティ(2)が観測でき、均等配分(ペナルティ0、1日ずつ)より
    #    悪化していることを直接確認できる
    sm_sc005_forced = constraints.build_model(minimal_config)
    penalty = objectives.add_sc005_half_day_workday_balance(sm_sc005_forced)
    for day in _half_days(sm_sc005_forced):
        sm_sc005_forced.model.add(
            sm_sc005_forced.works[("スタッフ1", day.key, "half")] == 1
        )
        sm_sc005_forced.model.add(
            sm_sc005_forced.works[("スタッフ2", day.key, "half")] == 0
        )
    weight = objectives.weight_for(minimal_config.optimization_mode, "sc005")
    sm_sc005_forced.model.minimize(weight * penalty)
    solver_sc005_forced = cp_model.CpSolver()
    status_sc005_forced = solver_sc005_forced.solve(sm_sc005_forced.model)
    assert status_sc005_forced == cp_model.OPTIMAL
    assert solver_sc005_forced.value(penalty) == 2, (
        "偏り配分(スタッフ1:2日・スタッフ2:0日)の"
        "max_half_days-min_half_days は2のはずです"
    )
    assert solver_sc005_forced.value(penalty) > 0, (
        "SC-005有効時は偏り配分が均等配分(ペナルティ0)より悪化するはずです"
    )


def test_sc005_no_half_days_returns_zero_penalty():
    """半日診療日が1日も無い設定では、SC-005ペナルティは常に0(整数リテラル)
    であること（変数を生成しないことの確認）。"""
    no_half_yaml = _MINIMAL_CONFIG_YAML.replace("thu: half", "thu: full").replace(
        "sat: half", "sat: closed"
    ).replace(
        """  - name: half
    day_types: [half]
    start: "09:00"
    end: "09:30"
    break_minutes: 0
""",
        "",
    )
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "no_half.yaml"
        path.write_text(no_half_yaml, encoding="utf-8")
        config = config_loader.load_config(path)
    sm = constraints.build_model(config)
    penalty = objectives.add_sc005_half_day_workday_balance(sm)
    assert penalty == 0


# --- 月次モデルでも共通実装で動作すること（週次・月次共通コード） -------------


def test_sc005_builds_on_monthly_model_without_error(sample_config):
    """月次モデル(DayContext.key=日付)でも SC-005 が同一コードで構築できること。"""
    monthly = calendar.load_monthly_schedule(SAMPLE_SCHEDULE, sample_config)
    calendar_days = calendar.expand_month(sample_config, monthly)
    sm = constraints.build_monthly_model(sample_config, calendar_days, monthly.vacations)
    penalty = objectives.add_sc005_half_day_workday_balance(sm)
    # max_half_days/min_half_days変数を必ず生成する実装のため、生成有無はこれで判別する
    assert not isinstance(penalty, int)


def test_engine_run_monthly_with_sc005_still_feasible(sample_config):
    """SC-001・SC-002・SC-004・SC-005を組み込んだ目的関数でも、月次モデルの
    求解が INFEASIBLE にならないこと（既存の月次シフト生成テストに対する
    回帰確認）。"""
    result = engine.run_monthly(sample_config, SAMPLE_SCHEDULE, time_limit_seconds=60.0)
    assert result["status"] in ("OPTIMAL", "FEASIBLE")
    assert result["schedule"] is not None
