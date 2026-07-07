"""スタッフ管理画面（P7-2）。

FR-01: スタッフマスタ（スキルスコア・勤務形態・週勤務日数）の表示・編集。
データソースは scheduler.staff_repository（staff.yaml, schema_version: 2）。
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from scheduler.staff_repository import (
    EMPLOYMENT_TYPES,
    MAX_WEEKLY_WORKDAYS,
    MIN_WEEKLY_WORKDAYS,
    SKILL_KEYS,
    StaffValidationError,
    load_staff,
    save_staff,
)

# テスト（AppTest）から一時ファイルへ差し替えるための環境変数オーバーライド。
# ファイルパス方式の st.Page はページ切替のたびにこのスクリプトを再実行するため、
# AppTest からは Python オブジェクトの直接差し替えができない（環境変数のみ有効）。
_STAFF_PATH_ENV = "CLINIC_STAFF_PATH"

DEFAULT_STAFF_PATH = Path(
    os.environ.get(_STAFF_PATH_ENV)
    or Path(__file__).resolve().parents[3] / "config" / "samples" / "sample_staff.yaml"
)

SKILL_LABELS = {
    "rehab": "リハビリ",
    "reception_am": "受付(午前)",
    "reception_pm": "受付(午後)",
    "general": "一般",
}


def render(staff_path: Path | str = DEFAULT_STAFF_PATH) -> None:
    """スタッフマスタの表示・編集画面を描画する。"""
    st.title("スタッフ管理")
    st.caption("スタッフマスタ（スキルスコア・勤務形態・週勤務日数）の表示・編集")

    staff_path = Path(staff_path)
    try:
        rows = load_staff(staff_path)
    except StaffValidationError as exc:
        st.error(f"スタッフマスタの読込に失敗しました: {exc}")
        return

    column_config = {
        "name": st.column_config.TextColumn("スタッフ名", required=True),
        "employment": st.column_config.SelectboxColumn(
            "勤務形態", options=list(EMPLOYMENT_TYPES), required=True
        ),
        "weekly_workdays": st.column_config.NumberColumn(
            "週勤務日数",
            min_value=MIN_WEEKLY_WORKDAYS,
            max_value=MAX_WEEKLY_WORKDAYS,
            step=1,
            required=True,
        ),
    }
    for key in SKILL_KEYS:
        column_config[key] = st.column_config.NumberColumn(
            SKILL_LABELS[key], min_value=0, max_value=100, step=1, required=True
        )

    edited_rows = st.data_editor(
        rows,
        num_rows="dynamic",
        column_config=column_config,
        key="staff_editor",
        width="stretch",
    )

    if st.button("保存", type="primary"):
        try:
            save_staff(staff_path, edited_rows)
        except StaffValidationError as exc:
            st.error(f"入力内容に誤りがあります: {exc}")
        else:
            st.success("スタッフマスタを保存しました。")


render()
