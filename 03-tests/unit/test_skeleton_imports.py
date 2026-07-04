"""プロジェクトスケルトンのモジュール構成テスト。

ARCHITECTURE.md 5 章のモジュール分割方針どおりに配置されたモジュール
（既存実装 + プレースホルダ）が import 可能であることを検証する。
モジュールの追加・改名時は本リストと ARCHITECTURE.md を同時に更新すること。
"""

import importlib

import pytest

MODULES = [
    # エンジン層（scheduler パッケージ）
    "scheduler",
    "scheduler.config_loader",
    "scheduler.constraints",
    "scheduler.engine",
    "scheduler.objectives",
    "scheduler.calendar",
    "scheduler.result",
    # 出力層（exporters / ui）
    "exporters",
    "exporters.csv_exporter",
    "exporters.excel_exporter",
    "ui",
    "ui.app",
    # CLI
    "cli",
]


@pytest.mark.parametrize("module_name", MODULES)
def test_module_importable(module_name):
    """各モジュールが import でき、モジュール分割方針と実体が一致していること。"""
    assert importlib.import_module(module_name) is not None
