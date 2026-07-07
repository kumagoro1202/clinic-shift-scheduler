"""ui/app.py（P7-1 スケルトン）の AppTest による起動確認。

ARCHITECTURE.md 4 章のテスト戦略（UI 層は Streamlit AppTest でヘッドレス検証）に
基づく最小限のテスト。個別画面が追加され次第、対応する test_ui_*.py を追加する。
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[2] / "02-src" / "ui" / "app.py"


def test_app_runs_without_exception():
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=10)
    assert not at.exception


def test_app_shows_title():
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=10)
    assert at.title[0].value == "クリニック シフト作成システム"
