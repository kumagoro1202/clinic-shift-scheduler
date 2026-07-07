"""Excel 出力・印刷画面（P7-6）。

FR-06: 月間勤務表の Excel 出力。出力対象は P7-5 のシフト編集画面が
`st.session_state["shift_generation_result"]["schedule"]` に保持する
最新のスケジュール（手動編集済みであれば編集後の値）であり、生成直後の
未編集値ではない。印刷レイアウト（用紙・向き）は画面から選択できる。
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import streamlit as st

from exporters.excel_exporter import write_excel
from scheduler import calendar, config_loader
from scheduler.config_loader import ConfigError

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

ORIENTATION_LABELS = {"landscape": "横", "portrait": "縦"}
PAPER_SIZES = ("A4", "A3")


def render(
    config_path: Path | str = DEFAULT_CONFIG_PATH,
    staff_path: Path | str = DEFAULT_STAFF_PATH,
    schedule_path: Path | str = DEFAULT_SCHEDULE_PATH,
) -> None:
    """Excel 出力・印刷画面を描画する。"""
    st.title("Excel 出力・印刷")
    st.caption("月間勤務表を Excel ファイルとして出力する（印刷用レイアウト仮案）")

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

    orientation = st.selectbox(
        "印刷の向き",
        options=list(ORIENTATION_LABELS),
        format_func=lambda o: ORIENTATION_LABELS[o],
        key="excel_export_orientation",
    )
    paper_size = st.selectbox("用紙サイズ", options=PAPER_SIZES, key="excel_export_paper_size")

    calendar_days_all = calendar.expand_month_all(config, monthly)
    schedule = result["schedule"]

    buffer = io.BytesIO()
    write_excel(
        config,
        calendar_days_all,
        monthly.vacations,
        schedule,
        monthly.target_month,
        buffer,
        orientation=orientation,
        paper_size=paper_size,
    )
    buffer.seek(0)

    st.download_button(
        "Excel ファイルをダウンロード",
        data=buffer,
        file_name=f"shift_{monthly.target_month}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )


render()
