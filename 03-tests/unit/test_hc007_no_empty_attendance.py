"""P6-6 修正: HC-007（空出勤防止）の回帰テスト。

SC-004（勤務回数均等化）は works（出勤）基準で最大最小差を最小化するが、
works自体にコストがかからないため、配置(assign)を一切伴わない出勤
（works=1, assign=0）を追加するだけで目的関数を改善できてしまう縮退解が
最適とみなされていた（P6-6で観測。スタッフCが水曜・土曜に空出勤する事例）。

本テストは、この縮退解が (1) HC-007 のハード制約により構造的に禁止されること、
(2) SC-004 の均等化圧力下でも実際に発生しないことを検証する。実在データは
使用しない。
"""

import pytest
from ortools.sat.python import cp_model

from scheduler import config_loader, constraints, objectives

# 2名構成・平日5日(mon〜fri)のみ営業。area_aの必要人数は毎日1人
# （1名の出勤で充足）。もう1名は本来なら出勤せずとも制約は満たされるため、
# SC-004の均等化圧力下で「配置を伴わない出勤」を追加する余地がある
# （HC-007導入前はこれが最適解として選好されていた）。
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
      mon:
        - { start: "09:00", end: "09:30", headcount: 1 }
      tue:
        - { start: "09:00", end: "09:30", headcount: 1 }
      wed:
        - { start: "09:00", end: "09:30", headcount: 1 }
      thu:
        - { start: "09:00", end: "09:30", headcount: 1 }
      fri:
        - { start: "09:00", end: "09:30", headcount: 1 }
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


@pytest.fixture
def minimal_config(tmp_path):
    path = tmp_path / "minimal_clinic.yaml"
    path.write_text(_MINIMAL_CONFIG_YAML, encoding="utf-8")
    return config_loader.load_config(path)


def _day_assign_sum(
    sm: constraints.ShiftModel,
    solver: cp_model.CpSolver,
    staff_name: str,
    day_key: str,
) -> int:
    return sum(
        solver.value(var)
        for (name, key, _, _), var in sm.assign.items()
        if name == staff_name and key == day_key
    )


# --- (1) HC-007 が「works=1・assign=0」を直接禁止すること ------------------


def test_hc007_forbids_works_without_any_assign(minimal_config):
    """特定staff・特定日でworks=1を強制しつつ、その日の全assignを0に固定すると
    INFEASIBLEになること（HC-007が空出勤を構造的に禁止していることの直接検証）。"""
    sm = constraints.build_model(minimal_config)
    target_day = next(d for d in sm.days if d.key == "wed")

    sm.model.add(sm.works[("スタッフ2", "wed", "day")] == 1)
    for (name, key, _, _), var in sm.assign.items():
        if name == "スタッフ2" and key == target_day.key:
            sm.model.add(var == 0)

    solver = cp_model.CpSolver()
    status = solver.solve(sm.model)
    assert status == cp_model.INFEASIBLE, (
        "HC-007導入後は works=1 かつ assign=0 の組み合わせは"
        "INFEASIBLEになるはずです"
    )


def test_without_hc007_works_without_assign_would_be_feasible(minimal_config):
    """対照実験: HC-007を課さない生の制約（HC-001〜004のみ）であれば
    works=1・assign=0はFEASIBLEであること（HC-007が真に追加的な制約で
    あることの確認。build_model自体はHC-007込みのため、ここでは
    HC-007抜きの構築ヘルパーで直接検証する）。"""
    sm = constraints.ShiftModel(
        config=minimal_config,
        days=constraints._weekly_day_contexts(minimal_config),
        vacation_kind=constraints._weekly_vacation_kind,
    )
    constraints._create_variables(sm)
    constraints.add_hc001_area_headcount(sm)
    constraints.add_hc002_single_assignment(sm)
    constraints.add_hc003_work_pattern(sm)
    constraints.add_hc004_vacations(sm)
    # HC-007は意図的に追加しない

    sm.model.add(sm.works[("スタッフ2", "wed", "day")] == 1)
    for (name, key, _, _), var in sm.assign.items():
        if name == "スタッフ2" and key == "wed":
            sm.model.add(var == 0)

    solver = cp_model.CpSolver()
    status = solver.solve(sm.model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE), (
        "HC-007なしでは works=1・assign=0 は許容されるはずです"
        "（この対照実験がFEASIBLEにならない場合、本テストの前提が誤っています）"
    )


# --- (2) SC-004均等化圧力下でも空出勤の解が実際に選好されないこと -----------


def test_sc004_balancing_no_longer_produces_empty_attendance(minimal_config):
    """SC-004の勤務回数均等化を有効にして最適解を求めても、
    いずれのstaff・日についても「works=1だがその日のassign合計が0」
    という状態(空出勤)が発生しないこと（P6-6で観測した縮退の再発防止）。"""
    sm = constraints.build_model(minimal_config)
    penalty = objectives.add_sc004_workday_balance(sm)
    weight = objectives.weight_for(minimal_config.optimization_mode, "sc004")
    sm.model.minimize(weight * penalty + sum(sm.assign.values()))

    solver = cp_model.CpSolver()
    status = solver.solve(sm.model)
    assert status == cp_model.OPTIMAL

    for staff in minimal_config.staff:
        for day in sm.days:
            patterns = constraints.patterns_for_day(minimal_config, day)
            day_works = sum(
                solver.value(sm.works[(staff.name, day.key, p.name)]) for p in patterns
            )
            if day_works >= 1:
                assign_sum = _day_assign_sum(sm, solver, staff.name, day.key)
                assert assign_sum >= 1, (
                    f"{staff.name} の {day.key} が空出勤(works=1, assign=0)に"
                    "なっています"
                )
