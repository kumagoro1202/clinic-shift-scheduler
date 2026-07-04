"""P6-5 SC-002（連続配置優先）のテスト。

テスト専用のサンプル設定（config/samples/sample_clinic.yaml・
config/samples/sample_schedule_202608.yaml）と、本テスト専用の最小構成
設定（2エリア・2名構成・3スロットのみ）を使用する。実在データは使用しない。
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

# 敵対的検証用の最小構成: 2名(スタッフ1・スタッフ2)が area_a・area_b 両方に配置可能。
# 3スロット(09:00/09:30/10:00)のうち、area_a は全スロットで headcount1、
# area_b は中央スロット(09:30)のみ headcount1。必要配置総数(4セル)は
# 「連続配置」（スタッフ1がarea_aを09:00-10:00通しで担当・スタッフ2が
# area_bの09:30のみ担当）でも「切替配置」（スタッフ1がarea_a→area_b→area_aと
# 切り替える）でも同じであり、SC-002なしのbaselineは両者を無差別に扱う。
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
  tue: closed
  wed: closed
  thu: closed
  fri: closed
  sat: closed
  sun: closed
shift_patterns:
  - name: day
    day_types: [full]
    start: "09:00"
    end: "10:30"
    break_minutes: 0
areas:
  - name: area_a
    required_skills: [area_a]
    requirements:
      mon:
        - { start: "09:00", end: "10:30", headcount: 1 }
      tue: []
      wed: []
      thu: []
      fri: []
      sat: []
      sun: []
  - name: area_b
    required_skills: [area_b]
    requirements:
      mon:
        - { start: "09:30", end: "10:00", headcount: 1 }
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
    skills: { area_a: 50, area_b: 50 }
    vacations: []
  - name: "スタッフ2"
    employment: full_time
    weekly_workdays: 7
    skills: { area_a: 50, area_b: 50 }
    vacations: []
"""

_T0 = 9 * 60  # "09:00"
_T1 = 9 * 60 + 30  # "09:30"
_T2 = 10 * 60  # "10:00"


@pytest.fixture(scope="module")
def sample_config():
    return config_loader.load_config(SAMPLE_CONFIG)


@pytest.fixture
def minimal_config(tmp_path):
    path = tmp_path / "minimal_clinic.yaml"
    path.write_text(_MINIMAL_CONFIG_YAML, encoding="utf-8")
    return config_loader.load_config(path)


# --- weight_for / プリセット -----------------------------------------------


def test_weight_presets_match_engine_design_table():
    """internal/engine-design.md 5章の重みプリセット表。SC-002は全モード固定30。"""
    assert objectives.weight_for("balance", "sc002") == 30
    assert objectives.weight_for("skill_focus", "sc002") == 30
    assert objectives.weight_for("days_focus", "sc002") == 30


# --- SC-002 目的関数が連続配置を誘導すること（本体） --------------------------


def test_sc002_objective_prefers_continuous_placement(minimal_config):
    """連続配置（スタッフ1がarea_aを09:00-10:00通しで担当・スタッフ2が
    area_bの09:30のみ担当）を強制した場合のSC-002ペナルティ(1)が、
    切替配置(3、下のテストで検証)より明確に小さいこと。

    連続配置でもペナルティが0にならない理由: area_bの必要配置(09:30のみ)を
    担当するスタッフは、その日の最初のスロット(09:00)には配置されないため、
    必ず1回分の「配置開始」が観測される（構造上避けられない）。それ以外の
    追加の切替(エリア切替・中抜け)が無ければペナルティは1に留まる。
    """
    forced_continuous = {
        ("スタッフ1", "mon", "area_a", _T0): 1,
        ("スタッフ1", "mon", "area_b", _T0): 0,
        ("スタッフ1", "mon", "area_a", _T1): 1,
        ("スタッフ1", "mon", "area_b", _T1): 0,
        ("スタッフ1", "mon", "area_a", _T2): 1,
        ("スタッフ1", "mon", "area_b", _T2): 0,
        ("スタッフ2", "mon", "area_a", _T0): 0,
        ("スタッフ2", "mon", "area_b", _T0): 0,
        ("スタッフ2", "mon", "area_a", _T1): 0,
        ("スタッフ2", "mon", "area_b", _T1): 1,
        ("スタッフ2", "mon", "area_a", _T2): 0,
        ("スタッフ2", "mon", "area_b", _T2): 0,
    }

    sm = constraints.build_model(minimal_config)
    penalty = objectives.add_sc002_continuous_placement(sm)
    for key, value in forced_continuous.items():
        sm.model.add(sm.assign[key] == value)
    weight = objectives.weight_for(minimal_config.optimization_mode, "sc002")
    sm.model.minimize(weight * penalty + sum(sm.assign.values()))

    solver = cp_model.CpSolver()
    status = solver.solve(sm.model)
    assert status == cp_model.OPTIMAL
    assert solver.value(penalty) == 1


def test_sc002_disabled_allows_switchy_assignment_as_optimal(minimal_config):
    """敵対的検証: SC-002目的関数を無効化(=baselineのみ)すると、エリアを
    切り替える配置(スタッフ1がarea_a→area_b→area_aと切替)も、連続配置と
    同じ最適値として許容されてしまうこと。SC-002を復元(有効化)すると、
    同じ強制配置のペナルティが明確に観測できる(切替のない解より悪化する)ことを
    確認する。"""
    forced_switchy = {
        ("スタッフ1", "mon", "area_a", _T0): 1,
        ("スタッフ1", "mon", "area_b", _T0): 0,
        ("スタッフ1", "mon", "area_a", _T1): 0,
        ("スタッフ1", "mon", "area_b", _T1): 1,
        ("スタッフ1", "mon", "area_a", _T2): 1,
        ("スタッフ1", "mon", "area_b", _T2): 0,
        ("スタッフ2", "mon", "area_a", _T0): 0,
        ("スタッフ2", "mon", "area_b", _T0): 0,
        ("スタッフ2", "mon", "area_a", _T1): 1,
        ("スタッフ2", "mon", "area_b", _T1): 0,
        ("スタッフ2", "mon", "area_a", _T2): 0,
        ("スタッフ2", "mon", "area_b", _T2): 0,
    }

    # 1) baseline のみ（SC-002なし）: 自由に解かせた最適値
    sm_free = constraints.build_model(minimal_config)
    sm_free.model.minimize(sum(sm_free.assign.values()))
    solver_free = cp_model.CpSolver()
    status_free = solver_free.solve(sm_free.model)
    assert status_free == cp_model.OPTIMAL
    baseline_optimal = solver_free.objective_value

    # 2) baseline のみで、切替配置を強制 -> 同じ最適値のはず
    #    （SC-002が無効な間は配置の連続性に無差別であることの確認）
    sm_forced = constraints.build_model(minimal_config)
    for key, value in forced_switchy.items():
        sm_forced.model.add(sm_forced.assign[key] == value)
    sm_forced.model.minimize(sum(sm_forced.assign.values()))
    solver_forced = cp_model.CpSolver()
    status_forced = solver_forced.solve(sm_forced.model)
    assert status_forced == cp_model.OPTIMAL
    assert solver_forced.objective_value == baseline_optimal, (
        "SC-002無効時は配置の連続性に無差別のはずが、"
        "切替配置(スタッフ1のarea_a→area_b→area_a)が baseline 最適解として"
        "許容されていません"
    )

    # 3) SC-002を復元（有効化）した上で同じ強制配置を評価
    #    -> 切替ペナルティ(3)が観測でき、連続配置(ペナルティ1)より
    #    悪化していることを直接確認できる
    sm_sc002_forced = constraints.build_model(minimal_config)
    penalty = objectives.add_sc002_continuous_placement(sm_sc002_forced)
    for key, value in forced_switchy.items():
        sm_sc002_forced.model.add(sm_sc002_forced.assign[key] == value)
    weight = objectives.weight_for(minimal_config.optimization_mode, "sc002")
    sm_sc002_forced.model.minimize(
        weight * penalty + sum(sm_sc002_forced.assign.values())
    )
    solver_sc002_forced = cp_model.CpSolver()
    status_sc002_forced = solver_sc002_forced.solve(sm_sc002_forced.model)
    assert status_sc002_forced == cp_model.OPTIMAL
    assert solver_sc002_forced.value(penalty) == 3, (
        "切替配置(スタッフ1: area_a@09:00 → area_b@09:30 → area_a@10:00 で2回の"
        "再開始、スタッフ2: area_a@09:30の1回の開始)の合計ペナルティは3のはずです"
    )
    assert solver_sc002_forced.objective_value > baseline_optimal, (
        "SC-002有効時は切替配置がbaseline最適値より悪化するはずです"
    )


# --- 月次モデルでも共通実装で動作すること（週次・月次共通コード） -------------


def test_sc002_builds_on_monthly_model_without_error(sample_config):
    """月次モデル(DayContext.key=日付)でも SC-002 が同一コードで構築できること。"""
    monthly = calendar.load_monthly_schedule(SAMPLE_SCHEDULE, sample_config)
    calendar_days = calendar.expand_month(sample_config, monthly)
    sm = constraints.build_monthly_model(sample_config, calendar_days, monthly.vacations)
    penalty = objectives.add_sc002_continuous_placement(sm)
    # start変数が1つも無ければ int の 0 を返す実装のため、生成有無はこれで判別する
    assert not isinstance(penalty, int)


def test_engine_run_monthly_with_sc002_still_feasible(sample_config):
    """SC-002を組み込んだ目的関数でも、月次モデルの求解が INFEASIBLE にならないこと
    （既存の月次シフト生成テストに対する回帰確認）。"""
    result = engine.run_monthly(sample_config, SAMPLE_SCHEDULE, time_limit_seconds=60.0)
    assert result["status"] in ("OPTIMAL", "FEASIBLE")
    assert result["schedule"] is not None
