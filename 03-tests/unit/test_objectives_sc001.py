"""P6-4 SC-001（スキルバランス）のテスト。

テスト専用のサンプル設定（config/samples/sample_clinic.yaml・
config/samples/sample_schedule_202608.yaml）と、本テスト専用の最小構成
設定（2名構成・1時間帯のみ）を使用する。実在データは使用しない。
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

# 敵対的検証用の最小構成: スタッフA(rehabスコア=70)・スタッフC(rehabスコア=90)の
# 2名のみが rehab に配置可能。target_avg を 70 に固定し、乖離ゼロの選択肢（A）と
# 乖離20の選択肢（C）を明確に区別できるようにする。ヘッドカウント1・単一スロット
# のみのbandとし、複数スロットにまたがる組み合わせの曖昧さを排除する。
_MINIMAL_CONFIG_YAML = """
schema_version: 1
work_rules:
  binding_hours: 4
  break_minutes: 0
  working_hours: 4
  break_window: { start: "09:00", end: "09:30" }
options:
  skill_balance:
    target_avg: { rehab: 70 }
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
    end: "13:00"
    break_minutes: 0
areas:
  - name: rehab
    required_skills: [rehab]
    requirements:
      mon:
        - { start: "09:00", end: "09:30", headcount: 1 }
      tue: []
      wed: []
      thu: []
      fri: []
      sat: []
      sun: []
staff:
  - name: "スタッフA"
    employment: full_time
    weekly_workdays: 7
    skills: { rehab: 70 }
    vacations: []
  - name: "スタッフC"
    employment: full_time
    weekly_workdays: 7
    skills: { rehab: 90 }
    vacations: []
"""

_SLOT = 9 * 60  # "09:00"


@pytest.fixture(scope="module")
def sample_config():
    return config_loader.load_config(SAMPLE_CONFIG)


@pytest.fixture
def minimal_config(tmp_path):
    path = tmp_path / "minimal_clinic.yaml"
    path.write_text(_MINIMAL_CONFIG_YAML, encoding="utf-8")
    return config_loader.load_config(path)


# --- 設定パース -----------------------------------------------------------


def test_config_default_optimization_mode_and_empty_skill_balance(sample_config):
    """options.optimization_mode / skill_balance を省略した場合の初期値。"""
    assert sample_config.optimization_mode == "balance"
    assert sample_config.skill_balance.target_avg == {}


def test_config_rejects_unknown_optimization_mode(tmp_path):
    bad_yaml = _MINIMAL_CONFIG_YAML.replace(
        "options:\n  skill_balance:",
        "options:\n  optimization_mode: bogus\n  skill_balance:",
    )
    path = tmp_path / "bad_clinic.yaml"
    path.write_text(bad_yaml, encoding="utf-8")
    with pytest.raises(config_loader.ConfigError, match="optimization_mode"):
        config_loader.load_config(path)


def test_minimal_config_skill_balance_override(minimal_config):
    assert minimal_config.skill_balance.target_avg == {"rehab": 70.0}


# --- weight_for / プリセット -----------------------------------------------


def test_weight_presets_match_engine_design_table():
    """internal/engine-design.md 5章の重みプリセット表（バランス/スキル重視/日数重視）。"""
    assert objectives.weight_for("balance", "sc001") == 100
    assert objectives.weight_for("skill_focus", "sc001") == 300
    assert objectives.weight_for("days_focus", "sc001") == 50


def test_weight_for_rejects_unknown_mode():
    with pytest.raises(ValueError, match="最適化モード"):
        objectives.weight_for("bogus_mode", "sc001")


# --- skill_target_avg -------------------------------------------------------


def test_skill_target_avg_defaults_to_all_staff_average(sample_config):
    """target_avg 未指定時は「対象スキルの全スタッフ平均」を使う。

    sample_clinic.yaml の rehab スコア: A=70, B=0, C=90, D=75, E=0 → 平均47.0
    （配置不可スタッフ(スコア0)も平均計算に含む。engine-design.md 4.2節）。
    """
    assert objectives.skill_target_avg(sample_config, "rehab") == pytest.approx(47.0)


def test_skill_target_avg_uses_config_override(minimal_config):
    assert objectives.skill_target_avg(minimal_config, "rehab") == 70.0


def test_skill_target_avg_unconfigured_skill_defaults_to_zero(minimal_config):
    assert objectives.skill_target_avg(minimal_config, "reception_am") == 0.0


# --- _skill_key_for_band -----------------------------------------------------


def test_skill_key_single_required_skill_area(sample_config):
    rehab = next(a for a in sample_config.areas if a.name == "rehab")
    for band in rehab.requirements["mon"]:
        assert objectives._skill_key_for_band(rehab, band) == "rehab"


def test_skill_key_reception_am_pm_split(sample_config):
    reception = next(a for a in sample_config.areas if a.name == "reception")
    bands = reception.requirements["mon"]
    # 08:30-12:30 (完全に午前) -> reception_am
    am_band = next(b for b in bands if b.window.start == config_loader.parse_time("08:30"))
    assert objectives._skill_key_for_band(reception, am_band) == "reception_am"
    # 15:30-18:30 (完全に午後) -> reception_pm
    pm_band = next(b for b in bands if b.window.start == config_loader.parse_time("15:30"))
    assert objectives._skill_key_for_band(reception, pm_band) == "reception_pm"


# --- SC-001 目的関数がスキルバランスを誘導すること（本体） --------------------


def test_sc001_objective_prefers_staff_closer_to_target(minimal_config):
    """乖離が小さいスタッフA(dev=0)が、baseline上は無差別なスタッフC(dev=20)より
    優先して選ばれること。"""
    sm = constraints.build_model(minimal_config)
    penalty = objectives.add_sc001_skill_balance(sm)
    weight = objectives.weight_for(minimal_config.optimization_mode, "sc001")
    sm.model.minimize(weight * penalty + sum(sm.assign.values()))

    solver = cp_model.CpSolver()
    status = solver.solve(sm.model)
    assert status == cp_model.OPTIMAL

    assign_a = sm.assign[("スタッフA", "mon", "rehab", _SLOT)]
    assign_c = sm.assign[("スタッフC", "mon", "rehab", _SLOT)]
    assert solver.value(assign_a) == 1
    assert solver.value(assign_c) == 0
    assert solver.value(penalty) == 0


def test_sc001_disabled_allows_imbalanced_assignment_as_optimal(minimal_config):
    """敵対的検証: SC-001目的関数を無効化(=baselineのみ)すると、スキル乖離の大きい
    配置(スタッフC)も同じ最適値として許容されてしまうこと。SC-001を復元(有効化)
    すると、同じ強制配置はもはや最適ではなくなる(乖離ペナルティが観測できる)こと
    を確認する。"""
    # 1) baseline のみ（SC-001なし）: 自由に解かせた最適値
    sm_free = constraints.build_model(minimal_config)
    sm_free.model.minimize(sum(sm_free.assign.values()))
    solver_free = cp_model.CpSolver()
    status_free = solver_free.solve(sm_free.model)
    assert status_free == cp_model.OPTIMAL
    baseline_optimal = solver_free.objective_value

    # 2) baseline のみで、乖離の大きいスタッフCを強制 -> 同じ最適値のはず
    #    （SC-001が無効な間はスキル配分に無差別であることの確認）
    sm_forced = constraints.build_model(minimal_config)
    forced_c = sm_forced.assign[("スタッフC", "mon", "rehab", _SLOT)]
    sm_forced.model.add(forced_c == 1)
    sm_forced.model.minimize(sum(sm_forced.assign.values()))
    solver_forced = cp_model.CpSolver()
    status_forced = solver_forced.solve(sm_forced.model)
    assert status_forced == cp_model.OPTIMAL
    assert solver_forced.objective_value == baseline_optimal, (
        "SC-001無効時はスキル配分に無差別のはずが、"
        "バランスの悪い配置(スタッフC)が baseline 最適解として"
        "許容されていません"
    )

    # 3) SC-001を復元（有効化）した上で同じ強制配置を評価 -> 乖離ペナルティ(20)が
    #    観測でき、バランスが悪化していることを直接確認できる
    sm_sc001_forced = constraints.build_model(minimal_config)
    penalty = objectives.add_sc001_skill_balance(sm_sc001_forced)
    forced_c2 = sm_sc001_forced.assign[("スタッフC", "mon", "rehab", _SLOT)]
    sm_sc001_forced.model.add(forced_c2 == 1)
    weight = objectives.weight_for(minimal_config.optimization_mode, "sc001")
    sm_sc001_forced.model.minimize(weight * penalty + sum(sm_sc001_forced.assign.values()))
    solver_sc001_forced = cp_model.CpSolver()
    status_sc001_forced = solver_sc001_forced.solve(sm_sc001_forced.model)
    assert status_sc001_forced == cp_model.OPTIMAL
    assert solver_sc001_forced.value(penalty) == 20, (
        "スタッフC(rehab=90)強制時の乖離は |90-70|=20 のはずです"
    )


# --- 月次モデルでも共通実装で動作すること（週次・月次共通コード） -------------


def test_sc001_builds_on_monthly_model_without_error(sample_config):
    """月次モデル(DayContext.key=日付)でも SC-001 が同一コードで構築できること。"""
    monthly = calendar.load_monthly_schedule(SAMPLE_SCHEDULE, sample_config)
    calendar_days = calendar.expand_month(sample_config, monthly)
    sm = constraints.build_monthly_model(sample_config, calendar_days, monthly.vacations)
    penalty = objectives.add_sc001_skill_balance(sm)
    # dev変数が1つも無ければ int の 0 を返す実装のため、生成有無はこれで判別する
    assert not isinstance(penalty, int)


def test_engine_run_monthly_with_sc001_still_feasible(sample_config):
    """SC-001を組み込んだ目的関数でも、月次モデルの求解が INFEASIBLE にならないこと
    （既存の月次シフト生成テストに対する回帰確認）。"""
    result = engine.run_monthly(sample_config, SAMPLE_SCHEDULE, time_limit_seconds=60.0)
    assert result["status"] in ("OPTIMAL", "FEASIBLE")
    assert result["schedule"] is not None
