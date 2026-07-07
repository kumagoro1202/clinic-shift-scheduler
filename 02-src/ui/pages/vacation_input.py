"""休暇入力画面（P7-3）。

FR-02: 日付単位の休暇登録（終日・午前休・午後休）の表示・編集。
データソースは scheduler.vacation_repository（schedule-YYYYMM.yaml,
schema_version: 2）。スタッフ選択は scheduler.staff_repository
（staff.yaml）と連携する。
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from scheduler.staff_repository import StaffValidationError, load_staff
from scheduler.vacation_repository import (
    VACATION_KINDS,
    VacationValidationError,
    load_schedule,
    save_schedule,
)

# テスト（AppTest）から一時ファイルへ差し替えるための環境変数オーバーライド。
_STAFF_PATH_ENV = "CLINIC_STAFF_PATH"
_SCHEDULE_PATH_ENV = "CLINIC_SCHEDULE_PATH"

DEFAULT_STAFF_PATH = Path(
    os.environ.get(_STAFF_PATH_ENV)
    or Path(__file__).resolve().parents[3] / "config" / "samples" / "sample_staff.yaml"
)
DEFAULT_SCHEDULE_PATH = Path(
    os.environ.get(_SCHEDULE_PATH_ENV)
    or Path(__file__).resolve().parents[3] / "config" / "samples" / "sample_schedule_202608.yaml"
)

KIND_LEGEND = "full=終日 / am=午前休 / pm=午後休"


def render(
    staff_path: Path | str = DEFAULT_STAFF_PATH,
    schedule_path: Path | str = DEFAULT_SCHEDULE_PATH,
) -> None:
    """休暇入力画面（日付単位の休暇登録）を描画する。"""
    st.title("休暇入力")
    st.caption("日付単位の休暇登録（終日・午前休・午後休）")

    staff_path = Path(staff_path)
    schedule_path = Path(schedule_path)

    try:
        staff_rows = load_staff(staff_path)
    except StaffValidationError as exc:
        st.error(f"スタッフマスタの読込に失敗しました: {exc}")
        return
    staff_names = [row["name"] for row in staff_rows]

    try:
        schedule = load_schedule(schedule_path)
    except VacationValidationError as exc:
        st.error(f"月次設定の読込に失敗しました: {exc}")
        return

    target_month = schedule["target_month"]
    st.text(f"対象月: {target_month}")
    st.caption(f"休暇種別（kind）: {KIND_LEGEND}")

    column_config = {
        "staff": st.column_config.SelectboxColumn(
            "スタッフ", options=staff_names, required=True
        ),
        "date": st.column_config.TextColumn(
            "休暇日", help="YYYY-MM-DD 形式（対象月内）", required=True
        ),
        "kind": st.column_config.SelectboxColumn(
            "種別", options=list(VACATION_KINDS), required=True
        ),
        "paid": st.column_config.CheckboxColumn("有給"),
    }

    edited_rows = st.data_editor(
        schedule["vacations"],
        num_rows="dynamic",
        column_config=column_config,
        key="vacation_editor",
        width="stretch",
    )

    if st.button("保存", type="primary"):
        try:
            save_schedule(
                schedule_path,
                target_month,
                edited_rows,
                schedule["raw"],
                staff_names,
            )
        except VacationValidationError as exc:
            st.error(f"入力内容に誤りがあります: {exc}")
        else:
            st.success("休暇登録を保存しました。")


render()
