"""管理者 UI エントリポイント（P7-1: Streamlit スケルトン / P7-2 以降: 画面追加）。

ARCHITECTURE.md 5 章のモジュール分割方針に基づくエントリポイント。
個別画面は `ui/pages/` 配下のスクリプトとして実装し、`st.navigation` +
`st.Page`（ファイルパス方式）によるマルチページ構成でここから結線する
（軍師申し送り: st.Page 方式を採用。ファイルパス方式は AppTest.switch_page
による画面単位のテスタビリティを公式にサポートしており、AppTest 側が
callable 方式のページ切替に未対応な現状（Streamlit 1.59 時点）と整合する）。
"""

from __future__ import annotations

import streamlit as st

APP_TITLE = "クリニック シフト作成システム"


def render_home() -> None:
    """トップ画面（ホーム）を描画する。"""
    st.title(APP_TITLE)
    st.caption("管理者向けシフト作成・編集システム")
    st.info(
        "左のナビゲーションから各画面を選択してください。"
        "シフト手動編集などの画面は、"
        "今後のフェーズ（P7-5 以降）で追加されます。"
    )


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    pages = [
        st.Page(render_home, title="ホーム", default=True),
        st.Page("pages/staff_management.py", title="スタッフ管理"),
        st.Page("pages/vacation_input.py", title="休暇入力"),
        st.Page("pages/shift_generation.py", title="シフト生成"),
    ]
    st.navigation(pages).run()


main()
