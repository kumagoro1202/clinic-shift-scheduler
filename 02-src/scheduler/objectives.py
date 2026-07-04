"""ソフト制約（SC-001〜005）と最適化モード別重みプリセット。

目的関数の全体形（`internal/engine-design.md` 4.1節）:
    minimize  Σ_i weight_i × penalty_i  （i ∈ SC-001, SC-002, SC-004, SC-005）
            + ε × Σ assign

本モジュールは SC-001（スキルバランス）のみを実装する。他の SC は
P6-5〜P6-8 で追加する。週次モデル（曜日キー）・月次モデル（日付キー）双方の
`DayContext` に対して同一コードで動作する（`ShiftModel.days` / `.weekday` /
`.key` のみを参照するため）。
"""

from __future__ import annotations

from ortools.sat.python import cp_model

from .config_loader import AM_PM_BOUNDARY_MINUTES, OPTIMIZATION_MODES, Area, Config, RequirementBand
from .constraints import ShiftModel

# 重みプリセット（`internal/engine-design.md` 5章）。SC-002/004/005はP6-5〜7で追加。
WEIGHT_PRESETS: dict[str, dict[str, int]] = {
    "balance": {"sc001": 100},
    "skill_focus": {"sc001": 300},
    "days_focus": {"sc001": 50},
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
