"""管理者 UI エントリポイント（P7-1: Streamlit スケルトン）。

ARCHITECTURE.md 5 章のモジュール分割方針に基づくエントリポイント。
個別画面（スタッフ管理・休暇入力・シフト生成・結果編集）は
`ui/pages/` 配下に P7-2 以降で追加する。本ファイルは骨格のみを持つ。
"""

from __future__ import annotations

import streamlit as st

APP_TITLE = "クリニック シフト作成システム"


def render() -> None:
    """アプリのトップ画面を描画する。"""
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.caption("管理者向けシフト作成・編集システム")
    st.info(
        "スタッフ管理・休暇入力・シフト生成・結果編集などの画面は、"
        "今後のフェーズ（P7-2 以降）で `ui/pages/` に追加されます。"
    )


render()
