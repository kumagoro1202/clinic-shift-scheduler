"""結合テストのプレースホルダ。

実テストは P6-9（シフト生成 CLI・CSV 出力）以降で追加する。
本テストは結合テストスイートが CI で収集・実行されることを保証する
（SKIP は使用しない。SKIP=FAIL ルールのため）。
"""


def test_integration_suite_is_collected():
    """結合テストディレクトリが pytest に収集されること。"""
    assert True
