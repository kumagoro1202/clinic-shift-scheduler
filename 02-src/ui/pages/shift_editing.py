"""シフト手動編集画面（P7-5）。

FR-05: 生成結果（P7-4 のシフト生成画面が session_state に保持する結果）を
表形式で手動編集し、ハード制約（HC-001〜004・スキル適性）違反を警告表示する。
編集結果に違反があっても保存自体は管理者判断で可能とする（強制ブロックは
しない。`external/output-design.md` 2 章）。

生成結果は `shift_generation.py` が `st.session_state["shift_generation_result"]`
に保持したものを参照する（同一ブラウザセッション内で共有される）。
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from exporters.csv_exporter import build_rows, rows_to_schedule
from scheduler import calendar, config_loader
from scheduler.config_loader import ConfigError
from scheduler.result import validate_hard_constraints

_CONFIG_PATH_ENV = "CLINIC_CONFIG_PATH"
_STAFF_PATH_ENV = "CLINIC_STAFF_PATH"
_SCHEDULE_PATH_ENV = "CLINIC_SCHEDULE_PATH"

DEFAULT_CONFIG_PATH = Path(
    os.environ.get(_CONFIG_PATH_ENV)
    or Path(__file__).resolve().parents[3] / "config" / "samples" / "sample_clinic.yaml"
)
DEFAULT_STAFF_PATH = Path(
    os.environ.get(_STAFF_PATH_ENV)
    or Path(__file__).resolve().parents[3] / "config" / "samples" / "sample_staff.yaml"
)
DEFAULT_SCHEDULE_PATH = Path(
    os.environ.get(_SCHEDULE_PATH_ENV)
    or Path(__file__).resolve().parents[3] / "config" / "samples" / "sample_schedule_202608.yaml"
)

RESULT_KEY = "shift_generation_result"


def render(
    config_path: Path | str = DEFAULT_CONFIG_PATH,
    staff_path: Path | str = DEFAULT_STAFF_PATH,
    schedule_path: Path | str = DEFAULT_SCHEDULE_PATH,
) -> None:
    """シフト手動編集画面を描画する。"""
    st.title("シフト編集")
    st.caption("生成結果の手動編集とハード制約違反チェック（保存は違反があっても可能）")

    result = st.session_state.get(RESULT_KEY)
    if result is None or result.get("schedule") is None:
        st.info("先に「シフト生成」画面でシフトを生成してください。")
        return

    config_path = Path(config_path)
    staff_path = Path(staff_path)
    schedule_path = Path(schedule_path)

    try:
        config = config_loader.load_config(config_path, staff_path=staff_path)
    except ConfigError as exc:
        st.error(f"診療所設定の読込に失敗しました: {exc}")
        return

    try:
        monthly = calendar.load_monthly_schedule(schedule_path, config)
    except ConfigError as exc:
        st.error(f"月次設定の読込に失敗しました: {exc}")
        return

    calendar_days = calendar.expand_month(config, monthly)
    schedule = result["schedule"]
    rows = build_rows(schedule, calendar_days)

    staff_names = [s.name for s in config.staff]
    area_names = [a.name for a in config.areas] + ["break"]
    pattern_names = [p.name for p in config.shift_patterns]

    column_config = {
        "date": st.column_config.TextColumn("日付", help="YYYY-MM-DD 形式", required=True),
        "weekday": st.column_config.TextColumn("曜日", disabled=True),
        "staff": st.column_config.SelectboxColumn(
            "スタッフ", options=staff_names, required=True
        ),
        "pattern": st.column_config.SelectboxColumn(
            "パターン", options=pattern_names, required=True
        ),
        "area": st.column_config.SelectboxColumn(
            "エリア", options=area_names, required=True
        ),
        "start": st.column_config.TextColumn("開始", help="HH:MM 形式", required=True),
        "end": st.column_config.TextColumn("終了", help="HH:MM 形式", required=True),
    }

    edited_rows = st.data_editor(
        rows,
        num_rows="dynamic",
        column_config=column_config,
        key="shift_editing_editor",
        width="stretch",
    )

    edited_schedule = rows_to_schedule(edited_rows)
    warnings = validate_hard_constraints(config, calendar_days, monthly.vacations, edited_schedule)

    st.subheader("ハード制約違反チェック")
    if warnings:
        st.warning(f"{len(warnings)} 件のハード制約違反があります（保存は可能です）。")
        st.dataframe(
            [
                {"種別": w.kind, "スタッフ": w.staff_name or "-", "内容": w.detail}
                for w in warnings
            ],
            width="stretch",
        )
    else:
        st.success("ハード制約違反はありません。")

    if st.button("保存", type="primary"):
        st.session_state[RESULT_KEY] = {**result, "schedule": edited_schedule}
        st.success("編集結果を保存しました（このセッション内で有効です）。")


render()
