"""ソフト制約（SC-001〜005）と最適化モード別重みプリセット。

目的関数の全体形（`internal/engine-design.md` 4.1節）:
    minimize  Σ_i weight_i × penalty_i  （i ∈ SC-001, SC-002, SC-004, SC-005）
            + ε × Σ assign

本モジュールは SC-001（スキルバランス）・SC-002（連続配置優先）・
SC-004（勤務回数均等化）・SC-005（半日診療日の均等分散）を実装する。週次モデル
（曜日キー）・月次モデル（日付キー）双方の `DayContext` に対して同一コードで
動作する（`ShiftModel.days` / `.weekday` / `.key` のみを参照するため）。
"""

from __future__ import annotations

from ortools.sat.python import cp_model

from .config_loader import AM_PM_BOUNDARY_MINUTES, OPTIMIZATION_MODES, Area, Config, RequirementBand
from .constraints import ShiftModel

# 重みプリセット（`internal/engine-design.md` 5章）。
# SC-002は全モードで重み30固定（全体スケールに対する影響を抑え、エリア切替の
# 最小化を「補助的な誘導」に留める設計判断。engine-design.md 5章）。
WEIGHT_PRESETS: dict[str, dict[str, int]] = {
    "balance": {"sc001": 100, "sc002": 30, "sc004": 100, "sc005": 50},
    "skill_focus": {"sc001": 300, "sc002": 30, "sc004": 50, "sc005": 25},
    "days_focus": {"sc001": 50, "sc002": 30, "sc004": 300, "sc005": 100},
}


def weight_for(mode: str, sc_id: str) -> int:
    """最適化モードにおける SC の重みを返す。"""
    if mode not in OPTIMIZATION_MODES:
        raise ValueError(f"未知の最適化モードです: {mode!r}（対応値: {OPTIMIZATION_MODES}）")
    return WEIGHT_PRESETS[mode][sc_id]


def _skill_key_for_band(area: Area, band: RequirementBand) -> str:
    """エリア・時間帯からスキルバランスの評価対象スキルキーを選ぶ。

    必要スキルが1つのエリア（例: rehab）は常にそのスキルを使う。
    複数持つエリア（例: reception の午前/午後）は band の中心時刻が
    午前/午後どちらに属するかで最初/最後のスキルキーを選ぶ
    （受付は医事能力優先の要件を反映。`engine-design.md` 4.2節）。
    """
    if len(area.required_skills) == 1:
        return area.required_skills[0]
    midpoint = (band.window.start + band.window.end) // 2
    if midpoint < AM_PM_BOUNDARY_MINUTES:
        return area.required_skills[0]
    return area.required_skills[-1]


def skill_target_avg(config: Config, skill_key: str) -> float:
    """target_avg: 設定での上書きがなければ、そのスキルの全スタッフ平均を使う。"""
    override = config.skill_balance.target_avg.get(skill_key)
    if override is not None:
        return override
    scores = [staff.skills.get(skill_key, 0) for staff in config.staff]
    return sum(scores) / len(scores) if scores else 0.0


def add_sc001_skill_balance(sm: ShiftModel) -> cp_model.LinearExprT:
    """SC-001: 各（日, エリア, band, スロット）について、配置スタッフのスキル合計 `S` と
    目標合計 `T = target_avg × headcount` の乖離をペナルティとする。

    CP-SAT は整数線形のみ扱えるため、平均の除算を「合計 × 定数」の比較へ変形し、
    乖離を表す整数変数 `dev`（`dev ≥ S − T` かつ `dev ≥ T − S`）を導入する。
    重み付けは呼び出し側（`engine.py`）が `weight_for()` で行う
    （目的関数の形 `Σ weight_i × penalty_i` に合わせるため、本関数は
    重み適用前の生のペナルティ合計 `Σ dev` を返す）。

    Returns:
        `Σ dev`（生成した dev 変数が1つもなければ 0）。
    """
    config = sm.config
    target_avg_cache: dict[str, float] = {}
    penalty_terms: list[cp_model.IntVar] = []

    for day in sm.days:
        for area in config.areas:
            for band in area.requirements[day.weekday]:
                skill_key = _skill_key_for_band(area, band)
                if skill_key not in target_avg_cache:
                    target_avg_cache[skill_key] = skill_target_avg(config, skill_key)
                target_total = round(target_avg_cache[skill_key] * band.headcount)

                for slot in sm.slots[day.key]:
                    if not band.window.contains(slot):
                        continue
                    members = [
                        (staff, sm.assign[(staff.name, day.key, area.name, slot)])
                        for staff in config.staff
                        if (staff.name, day.key, area.name, slot) in sm.assign
                    ]
                    if not members:
                        continue
                    skill_sum = sum(
                        staff.skills.get(skill_key, 0) * var for staff, var in members
                    )
                    max_skill_sum = sum(staff.skills.get(skill_key, 0) for staff, _ in members)
                    upper_bound = max(max_skill_sum, target_total)
                    dev = sm.model.new_int_var(
                        0,
                        upper_bound,
                        f"sc001_dev_{day.key}_{area.name}_{slot}",
                    )
                    sm.model.add(dev >= skill_sum - target_total)
                    sm.model.add(dev >= target_total - skill_sum)
                    penalty_terms.append(dev)

    return sum(penalty_terms) if penalty_terms else 0


def add_sc002_continuous_placement(sm: ShiftModel) -> cp_model.LinearExprT:
    """SC-002: 同一日内のエリア切替回数（中抜けを含む）を最小化する。

    各（staff, 日, エリア）について、日内のスロット列（`sm.slots[day.key]` の
    ソート順）を隣接ペアで走査し、開始検出変数 `start ≥ assign[t] − assign[t−step]`
    を導入する。日内の `Σ start`（= 連続配置ブロック数）をペナルティとする
    （ブロック数最小化はエリア切替・中抜けの最小化と等価。`engine-design.md` 4.2節）。

    ウィンドウの最初のスロット（隣接ペアの片方の assign 変数が存在しない箇所）は
    ペナルティ対象外とする（勤務開始自体は「切替」ではないため）。
    重み付けは呼び出し側（`engine.py`）が `weight_for()` で行う。

    Returns:
        `Σ start`（生成した start 変数が1つもなければ 0）。
    """
    config = sm.config
    step = config.slot_minutes
    penalty_terms: list[cp_model.IntVar] = []

    for day in sm.days:
        slots = sm.slots[day.key]
        for staff in config.staff:
            for area in config.areas:
                for i in range(1, len(slots)):
                    prev_slot, curr_slot = slots[i - 1], slots[i]
                    if curr_slot - prev_slot != step:
                        continue
                    prev_key = (staff.name, day.key, area.name, prev_slot)
                    curr_key = (staff.name, day.key, area.name, curr_slot)
                    if prev_key not in sm.assign or curr_key not in sm.assign:
                        continue
                    start = sm.model.new_bool_var(
                        f"sc002_start_{staff.name}_{day.key}_{area.name}_{curr_slot}"
                    )
                    sm.model.add(start >= sm.assign[curr_key] - sm.assign[prev_key])
                    penalty_terms.append(start)

    return sum(penalty_terms) if penalty_terms else 0


def add_sc004_workday_balance(sm: ShiftModel) -> cp_model.LinearExprT:
    """SC-004: 全 staff の勤務日数（`Σ works`）の最大最小差を最小化する。

    各 staff について `Σ works(staff)`（`sm.works` は当該 staff・当該日の
    どのパターンで勤務するかを表す bool 変数で、日ごとに高々1つが真になる
    ため、日キーを問わず合計すれば勤務日数になる）を求め、全 staff に共通の
    整数変数 `max_days ≥ Σ works(staff)` ・ `min_days ≤ Σ works(staff)` を
    導入し、`max_days − min_days`（最大最小差）をペナルティとする
    （`engine-design.md` 4.2節）。

    `weekly_workdays` 比での正規化は行わない（パート・正職員の基準日数が
    異なる場合の影響はサンプルデータで評価済み。テスト・実行結果を参照）。
    重み付けは呼び出し側（`engine.py`）が `weight_for()` で行う。

    Returns:
        `max_days − min_days`（staff が1名もいなければ 0）。
    """
    config = sm.config
    if not config.staff:
        return 0

    max_total = len(sm.days)
    totals_per_staff: list[cp_model.LinearExprT] = []
    for staff in config.staff:
        terms = [
            var
            for (name, _day_key, _pattern_name), var in sm.works.items()
            if name == staff.name
        ]
        totals_per_staff.append(sum(terms) if terms else 0)

    max_days = sm.model.new_int_var(0, max_total, "sc004_max_days")
    min_days = sm.model.new_int_var(0, max_total, "sc004_min_days")
    for total in totals_per_staff:
        sm.model.add(max_days >= total)
        sm.model.add(min_days <= total)

    return max_days - min_days


def add_sc005_half_day_workday_balance(sm: ShiftModel) -> cp_model.LinearExprT:
    """SC-005: 半日診療日（`day.day_type == "half"`）における全 staff の出勤回数
    （`Σ works`、対象日を半日診療日に限定）の最大最小差を最小化する。

    SC-004（勤務回数均等化）と同形だが、対象日を半日診療日に限定する点のみ
    異なる（`engine-design.md` 4.2節。木曜・土曜出勤の偏りは SC-004 の総日数
    均等化では防げないため独立の制約とする）。HC-007（出勤日には配置を伴う
    ことの強制）は日種別を問わず全日に適用済みのため、SC-005 についても
    空出勤による縮退は構造的に防止されている（`engine-design.md` 3.1節）。
    重み付けは呼び出し側（`engine.py`）が `weight_for()` で行う。

    Returns:
        `max_half_days − min_half_days`（staff が1名もいない、または半日診療日が
        1日もなければ 0）。
    """
    config = sm.config
    half_day_keys = {day.key for day in sm.days if day.day_type == "half"}
    if not config.staff or not half_day_keys:
        return 0

    max_total = len(half_day_keys)
    totals_per_staff: list[cp_model.LinearExprT] = []
    for staff in config.staff:
        terms = [
            var
            for (name, day_key, _pattern_name), var in sm.works.items()
            if name == staff.name and day_key in half_day_keys
        ]
        totals_per_staff.append(sum(terms) if terms else 0)

    max_half_days = sm.model.new_int_var(0, max_total, "sc005_max_half_days")
    min_half_days = sm.model.new_int_var(0, max_total, "sc005_min_half_days")
    for total in totals_per_staff:
        sm.model.add(max_half_days >= total)
        sm.model.add(min_half_days <= total)

    return max_half_days - min_half_days
