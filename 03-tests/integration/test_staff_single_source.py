"""スタッフデータソース統合の中核テスト。

P7-2 管理者 UI（スタッフ管理画面）は staff_repository 経由で
staff.yaml（schema_version: 2）を編集する一方、P6 エンジン
（config_loader.load_config）は診療所設定（clinic.yaml）に埋め込まれた
独自の `staff:` セクションを参照しており、UI での編集がシフト生成へ
反映されない二重データソース問題があった。

本テストは、config_loader.load_config() に staff_path を指定することで
staff.yaml を単一ソースとして解決し、staff_repository 経由の編集が
engine.run_monthly の生成結果へ反映されることを検証する。
"""

from __future__ import annotations

import shutil
from pathlib import Path

from scheduler import config_loader, engine
from scheduler.staff_repository import load_staff, save_staff

SAMPLE_CONFIG = (
    Path(__file__).resolve().parents[2] / "config" / "samples" / "sample_clinic.yaml"
)
SAMPLE_STAFF = (
    Path(__file__).resolve().parents[2] / "config" / "samples" / "sample_staff.yaml"
)
SAMPLE_SCHEDULE = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "samples"
    / "sample_schedule_202608.yaml"
)

ORIGINAL_STAFF_NAMES = {"スタッフA", "スタッフB", "スタッフC", "スタッフD", "スタッフE"}


def _assigned_staff_names(schedule: dict) -> set[str]:
    return {name for day_result in schedule.values() for name in day_result}


def test_staff_yaml_edit_via_repository_is_reflected_in_monthly_generation(
    tmp_path: Path,
) -> None:
    """staff_repository 経由の編集(UI が実際に呼ぶ経路)が
    engine.run_monthly の生成結果に反映されることを検証する。

    sample_schedule_202608.yaml の休暇入力は「スタッフA」「スタッフB」を
    参照しているため、それらに影響しない「スタッフC」を改名して検証する。
    """
    staff_path = tmp_path / "staff.yaml"
    shutil.copy(SAMPLE_STAFF, staff_path)

    rows = load_staff(staff_path)
    assert {row["name"] for row in rows} == ORIGINAL_STAFF_NAMES
    for row in rows:
        if row["name"] == "スタッフC":
            row["name"] = "スタッフC2"
    save_staff(staff_path, rows)

    config = config_loader.load_config(SAMPLE_CONFIG, staff_path=staff_path)
    assert {s.name for s in config.staff} == {
        "スタッフA",
        "スタッフB",
        "スタッフC2",
        "スタッフD",
        "スタッフE",
    }

    result = engine.run_monthly(config, SAMPLE_SCHEDULE, time_limit_seconds=30.0)
    assert result["schedule"] is not None, (
        f"生成不可でした（status={result['status']}）。テスト用データを見直してください。"
    )

    assigned_names = _assigned_staff_names(result["schedule"])
    assert "スタッフC2" in assigned_names, (
        "staff.yaml で改名したスタッフが生成結果に含まれていません"
        "（UI 編集が engine.run_monthly に反映されていない可能性）"
    )
    assert "スタッフC" not in assigned_names, (
        "改名前のスタッフ名が残っています（clinic.yaml 埋込 staff が"
        "誤って参照されている可能性）"
    )


def test_load_config_without_staff_path_keeps_clinic_yaml_embedded_staff(
    tmp_path: Path,
) -> None:
    """staff_path 省略時は従来どおり clinic.yaml 埋込 staff を読み込む
    （週次モデル・後方互換の確認）。staff.yaml 側だけを書き換えても
    config には影響しないこと。
    """
    staff_path = tmp_path / "staff.yaml"
    shutil.copy(SAMPLE_STAFF, staff_path)
    rows = load_staff(staff_path)
    for row in rows:
        if row["name"] == "スタッフC":
            row["name"] = "スタッフC2"
    save_staff(staff_path, rows)

    config = config_loader.load_config(SAMPLE_CONFIG)
    assert {s.name for s in config.staff} == ORIGINAL_STAFF_NAMES
