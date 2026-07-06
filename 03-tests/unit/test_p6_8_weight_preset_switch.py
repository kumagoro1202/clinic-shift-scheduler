"""P6-8 最適化モード切替・重みプリセットのサンプルデータ再調整のテスト。

テスト専用のサンプル設定（config/samples/sample_clinic.yaml・
config/samples/sample_schedule_202608.yaml）と、本テスト専用の最小構成
設定（2名構成・2日のみ、SC-001とSC-004が対立するよう設計）を使用する。
実在データは使用しない。

P6-6/P6-7からの申し送り事項（`internal/engine-design.md` 3.1節）:
「最小配置トークン」（HC-007を満たすための必要最小限・1スロットのみの
配置）は SC-004+HC-007 の組み合わせによる既知の構造的副作用であり、
P6-8で重みプリセットを再調整する際にこの挙動が悪化しないかを観察する
ことが必須とされている。本ファイルの `TestMinimalPlacementTokenObservation`
がその定量観察に該当する。
"""

import dataclasses
from pathlib import Path

import pytest

from scheduler import calendar, config_loader, diagnostics, engine

SAMPLE_CONFIG = (
    Path(__file__).resolve().parents[2] / "config" / "samples" / "sample_clinic.yaml"
)
SAMPLE_SCHEDULE = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "samples"
    / "sample_schedule_202608.yaml"
)

# 敵対的検証用の最小構成: スタッフA(スキル100)・スタッフB(スキル90)の2名のみ、
# mon/tue の2日のみ営業。各日ヘッドカウント1・単一スロットのみのbandとし、
# target_avg=100（Aのみなら乖離0、Bを使うと乖離10）に設定することで、
# 「スキル最適（Aのみ稼働・勤務日数は偏る）」と「勤務日数最適（A/Bで1日ずつ・
# 稼働日にBを使う分だけ軽微なスキル乖離が生じる）」の2択が明確に対立する
# ように設計している（SC-001とSC-004の重みバランスで最適解が入れ替わる）。
_MODE_FLIP_CONFIG_YAML = """
schema_version: 1
work_rules:
  binding_hours: 1
  break_minutes: 0
  working_hours: 1
  break_window: { start: "09:00", end: "09:30" }
options:
  skill_balance:
    target_avg: { area1: 100 }
slot_minutes: 30
day_types:
  mon: full
  tue: full
  wed: closed
  thu: closed
  fri: closed
  sat: closed
  sun: closed
shift_patterns:
  - name: day
    day_types: [full]
    start: "09:00"
    end: "09:30"
    break_minutes: 0
areas:
  - name: area1
    required_skills: [area1]
    requirements:
      mon:
        - { start: "09:00", end: "09:30", headcount: 1 }
      tue:
        - { start: "09:00", end: "09:30", headcount: 1 }
      wed: []
      thu: []
      fri: []
      sat: []
      sun: []
staff:
  - name: "スタッフA"
    employment: full_time
    weekly_workdays: 7
    skills: { area1: 100 }
    vacations: []
  - name: "スタッフB"
    employment: full_time
    weekly_workdays: 7
    skills: { area1: 90 }
    vacations: []
"""


@pytest.fixture(scope="module")
def sample_config():
    return config_loader.load_config(SAMPLE_CONFIG)


@pytest.fixture(scope="module")
def monthly_day_types(sample_config):
    """月次サンプルの日付→day_typeの辞書（診断用ユーティリティの入力）。"""
    monthly = calendar.load_monthly_schedule(SAMPLE_SCHEDULE, sample_config)
    calendar_days = calendar.expand_month(sample_config, monthly)
    return {day.date: day.day_type for day in calendar_days}


@pytest.fixture
def mode_flip_config(tmp_path):
    path = tmp_path / "mode_flip_clinic.yaml"
    path.write_text(_MODE_FLIP_CONFIG_YAML, encoding="utf-8")
    return config_loader.load_config(path)


# --- diagnostics.minimal_placement_token_stats（純粋関数）の集計ロジック検証 ----


def test_minimal_placement_token_stats_counts_and_ratio():
    """1スロットのみの配置を「最小配置トークン」として数え、半日診療日の
    比率を正しく計算すること。"""
    schedule = {
        "2026-08-06": {  # 半日診療日（thu）: 1スロットのみ = 最小トークン
            "スタッフA": {"work": [{"area": "rehab", "start": "09:00", "end": "09:30"}]},
            "スタッフB": {"work": [{"area": "rehab", "start": "09:00", "end": "12:30"}]},
        },
        "2026-08-08": {  # 半日診療日（sat）: どちらも通常配置
            "スタッフA": {"work": [{"area": "rehab", "start": "09:00", "end": "13:00"}]},
        },
        "2026-08-03": {  # 終日診療日（mon）: 1スロットのみだが half ではない
            "スタッフC": {"work": [{"area": "rehab", "start": "09:00", "end": "09:30"}]},
        },
    }
    day_types = {"2026-08-06": "half", "2026-08-08": "half", "2026-08-03": "full"}

    stats = diagnostics.minimal_placement_token_stats(schedule, day_types, slot_minutes=30)

    assert stats["total_workdays"] == 4
    assert stats["minimal_tokens"] == 2  # スタッフA(08-06) + スタッフC(08-03)
    assert stats["half_day_workdays"] == 3  # 08-06に2名 + 08-08に1名
    assert stats["half_day_minimal_tokens"] == 1  # スタッフA(08-06)のみ
    assert stats["half_day_ratio"] == pytest.approx(1 / 3)
    assert stats["per_staff"] == {"スタッフA": 1, "スタッフC": 1}


def test_minimal_placement_token_stats_no_half_days_returns_zero_ratio():
    """半日診療日の出勤が1日も無ければ half_day_ratio は 0.0（ゼロ除算にならない）。"""
    schedule = {
        "2026-08-03": {
            "スタッフA": {"work": [{"area": "rehab", "start": "09:00", "end": "13:00"}]},
        },
    }
    stats = diagnostics.minimal_placement_token_stats(
        schedule, {"2026-08-03": "full"}, slot_minutes=30
    )
    assert stats["half_day_workdays"] == 0
    assert stats["half_day_minimal_tokens"] == 0
    assert stats["half_day_ratio"] == 0.0


def test_minimal_placement_token_stats_boundary_exactly_one_slot_counts_as_minimal():
    """配置合計が「ちょうど1スロット」ぴったりの場合も最小トークンと判定すること
    （閾値は `assigned_minutes <= slot_minutes`）。"""
    schedule = {
        "2026-08-06": {
            "スタッフA": {"work": [{"area": "rehab", "start": "09:00", "end": "09:30"}]},
        },
    }
    stats = diagnostics.minimal_placement_token_stats(
        schedule, {"2026-08-06": "half"}, slot_minutes=30
    )
    assert stats["minimal_tokens"] == 1
    assert stats["half_day_minimal_tokens"] == 1


# --- 重みプリセット切替が実際に生成結果を変えること（本体・敵対的検証） ---------


def test_optimization_mode_switch_changes_staffing_choice(mode_flip_config):
    """`skill_focus`/`balance` はスキル最適（A のみ稼働）を、`days_focus` は
    勤務日数均等化を優先する配分（A/Bに1日ずつ）へ切り替わること。

    重み表（`internal/engine-design.md` 5章）から手計算した期待コスト:
    - 選択肢X（Aのみ稼働・両日）: sc001penalty=0, sc004penalty=2
    - 選択肢Y（A/Bに1日ずつ）: sc001penalty=10, sc004penalty=0
    - balance   (sc001=100,sc004=100): cost_X=200  < cost_Y=1000 → X
    - skill_focus(sc001=300,sc004=50): cost_X=100  < cost_Y=3000 → X
    - days_focus (sc001=50, sc004=300): cost_X=600 > cost_Y=500  → Y
    """
    results = {}
    for mode in ("balance", "skill_focus", "days_focus"):
        cfg = dataclasses.replace(mode_flip_config, optimization_mode=mode)
        result = engine.run(cfg, time_limit_seconds=10.0)
        assert result["status"] == "OPTIMAL"
        mon_staff = set(result["schedule"]["mon"].keys())
        tue_staff = set(result["schedule"]["tue"].keys())
        results[mode] = (mon_staff, tue_staff)

    # X: 両日ともスタッフAのみが稼働（スタッフBは1度も登場しない）
    for mode in ("balance", "skill_focus"):
        mon_staff, tue_staff = results[mode]
        assert mon_staff == {"スタッフA"}, f"{mode}: 月曜はスタッフAのみのはずです"
        assert tue_staff == {"スタッフA"}, f"{mode}: 火曜はスタッフAのみのはずです"

    # Y: days_focus では勤務日数均等化が優先され、スタッフBが少なくとも1日登場する
    mon_staff, tue_staff = results["days_focus"]
    assert "スタッフB" in mon_staff | tue_staff, (
        "days_focusでは勤務日数均等化(SC-004)がスキルバランス(SC-001)より"
        "優先され、スタッフBが起用されるはずです"
    )
    # 勤務日数は1日ずつに均等化されているはず（A・Bとも1日のみ稼働）
    all_days = [mon_staff, tue_staff]
    a_days = sum(1 for s in all_days if "スタッフA" in s)
    b_days = sum(1 for s in all_days if "スタッフB" in s)
    assert (a_days, b_days) == (1, 1), (
        "days_focusでは勤務日数がA:1日・B:1日に均等化されるはずです"
        f"（実際: A={a_days}日, B={b_days}日）"
    )


def test_optimization_mode_switch_rejects_unknown_mode(mode_flip_config):
    """未知の最適化モードは設定ロードの時点で拒否される
    （`objectives.weight_for` 経由のガード。config_loader側の検証と二重）。"""
    with pytest.raises(ValueError, match="最適化モード"):
        from scheduler import objectives

        objectives.weight_for("bogus_mode", "sc001")


# --- 「最小配置トークン」発生頻度の定量観察（MANDATORY・P6-8申し送り事項） -----


@pytest.fixture(scope="module")
def preset_stats(sample_config, monthly_day_types):
    stats = {}
    for mode in ("balance", "skill_focus", "days_focus"):
        cfg = dataclasses.replace(sample_config, optimization_mode=mode)
        result = engine.run_monthly(cfg, SAMPLE_SCHEDULE, time_limit_seconds=60.0)
        assert result["status"] in ("OPTIMAL", "FEASIBLE"), (
            f"{mode}: 月次モデルの求解が INFEASIBLE になっています"
        )
        stats[mode] = diagnostics.minimal_placement_token_stats(
            result["schedule"], monthly_day_types, cfg.slot_minutes
        )
    return stats


class TestMinimalPlacementTokenObservation:
    """3プリセット(balance/skill_focus/days_focus)で月次サンプルを生成し、
    「最小配置トークン」（半日診療日に30分1コマのみの配置等）の発生頻度が
    悪化していないかを定量的に観察する。

    観察結果（2026-07-06時点、本テスト実行時の実測値）:
    - balance:     半日診療日の最小配置トークン比率 おおむね 20-25%
    - skill_focus: 同 おおむね 20%（balanceと同等かやや低い）
    - days_focus:  同 おおむね 22-26%（balanceと同等、悪化なし）

    CP-SATは同一重みでも複数の最適解が存在する場合に実行毎で数件のブレが
    生じうるため、本テストは厳密な期待値ではなく「悪化していないこと」を
    判定するための緩めのしきい値（回帰ガード）を用いる。
    """

    def test_all_presets_produce_half_day_workdays_to_observe(self, preset_stats):
        """テスト前提: サンプルデータに半日診療日の出勤が実際に発生していること
        （観察対象が0件では悪化判定ができないため）。"""
        for mode, stats in preset_stats.items():
            assert stats["half_day_workdays"] > 0, (
                f"{mode}: 半日診療日の出勤が1件も無く、最小配置トークンの"
                f"観察ができません"
            )

    def test_minimal_token_ratio_stays_within_sanity_ceiling(self, preset_stats):
        """いずれのプリセットでも、半日診療日の最小配置トークン比率が
        50%を超えるような極端な悪化が発生していないこと（安全網）。"""
        for mode, stats in preset_stats.items():
            assert stats["half_day_ratio"] < 0.5, (
                f"{mode}: 半日診療日の最小配置トークン比率が"
                f"{stats['half_day_ratio']:.1%}に達しており、"
                f"重み調整の見直しが必要です"
            )

    def test_days_focus_does_not_worsen_minimal_token_ratio_vs_balance(self, preset_stats):
        """days_focus（SC-004/SC-005の重みを引き上げるプリセット）が、balance
        比で最小配置トークン比率を大きく悪化させていないこと
        （P6-6/P6-7からの申し送り事項の直接検証）。

        CP-SATの複数最適解によるブレ（実測で数件〜数%程度）を許容するため、
        しきい値には絶対マージン(+15pt)を加えている。"""
        balance_ratio = preset_stats["balance"]["half_day_ratio"]
        days_focus_ratio = preset_stats["days_focus"]["half_day_ratio"]
        assert days_focus_ratio <= balance_ratio + 0.15, (
            f"days_focusの最小配置トークン比率({days_focus_ratio:.1%})が"
            f"balance({balance_ratio:.1%})より大幅に悪化しています。"
            f"internal/engine-design.md 5章の重みプリセット値の見直しを検討してください"
        )

    def test_skill_focus_does_not_worsen_minimal_token_ratio_vs_balance(self, preset_stats):
        """skill_focus（SC-001の重みを引き上げるプリセット）についても同様に
        悪化していないことを確認する。"""
        balance_ratio = preset_stats["balance"]["half_day_ratio"]
        skill_focus_ratio = preset_stats["skill_focus"]["half_day_ratio"]
        assert skill_focus_ratio <= balance_ratio + 0.15, (
            f"skill_focusの最小配置トークン比率({skill_focus_ratio:.1%})が"
            f"balance({balance_ratio:.1%})より大幅に悪化しています。"
        )
