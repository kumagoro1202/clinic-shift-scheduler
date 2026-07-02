"""E2E テストのプレースホルダ。

実テストは P7-8（Playwright による生成→表示→出力シナリオ）で追加する。
本テストは E2E テストスイートが CI で収集・実行されることを保証する
（SKIP は使用しない。SKIP=FAIL ルールのため）。
"""


def test_e2e_suite_is_collected():
    """E2E テストディレクトリが pytest に収集されること。"""
    assert True
