"""シフト生成・結果表示画面（P7-4・P7-7）。

FR-03: 対象月・最適化モードを指定して生成実行し、結果を表形式で表示する。
INFEASIBLE 時は `scheduler.infeasible_hints` による要因の手がかりを表示する。
FR-07: `weekly_hours_check` が有効な場合、生成結果に対して週40時間超過の
警告を表示する（SC-003。強制ブロックはしない。P7-7）。

データソースは scheduler.config_loader（診療所設定）と scheduler.calendar /
scheduler.engine（月次入力・生成エンジン）。対象月は月次入力ファイル
（schedule-YYYYMM.yaml）側で決まるため、本画面では読み込んだファイルの
対象月を表示し、最適化モードのみを画面から選択する（P7-2/P7-3 と同様、
1 ファイルを対象とする運用）。

スタッフ定義は staff.yaml（P7-2 スタッフ管理画面が経由する
scheduler.staff_repository, schema_version: 2）を単一ソースとして
config_loader.load_config() へ渡す。診療所設定（clinic.yaml）側の
`staff:` セクションはこの画面では使用しない（🚨#31: 二重データソース
問題の解消）。
"""

from __future__ import annotations

import dataclasses
import os
import time
from pathlib import Path

import streamlit as st

from exporters.csv_exporter import build_rows
from scheduler import calendar, config_loader, engine
from scheduler.config_loader import OPTIMIZATION_MODES, ConfigError
from scheduler.infeasible_hints import (
    compute_headcount_deficit_hints,
    compute_vacation_concentration_hints,
)
from scheduler.result import validate_hard_constraints

# テスト（AppTest）から一時ファイルへ差し替えるための環境変数オーバーライド。
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

MODE_LABELS = {"balance": "バランス", "skill_focus": "スキル重視", "days_focus": "日数重視"}

DEFAULT_TIME_LIMIT_SECONDS = 55.0


def render(
    config_path: Path | str = DEFAULT_CONFIG_PATH,
    staff_path: Path | str = DEFAULT_STAFF_PATH,
    schedule_path: Path | str = DEFAULT_SCHEDULE_PATH,
) -> None:
    """シフト生成・結果表示画面を描画する。"""
    st.title("シフト生成")
    st.caption("対象月・最適化モードを指定して生成実行し、結果を表形式で表示する")

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

    st.text(f"対象月: {monthly.target_month}")

    mode = st.selectbox(
        "最適化モード",
        options=list(OPTIMIZATION_MODES),
        format_func=lambda m: MODE_LABELS.get(m, m),
        index=list(OPTIMIZATION_MODES).index(config.optimization_mode),
        key="optimization_mode",
    )

    if st.button("生成実行", type="primary"):
        run_config = dataclasses.replace(config, optimization_mode=mode)
        with st.spinner("シフトを生成しています…"):
            started = time.monotonic()
            result = engine.run_monthly(
                run_config, schedule_path, time_limit_seconds=DEFAULT_TIME_LIMIT_SECONDS
            )
            elapsed = time.monotonic() - started
        st.session_state["shift_generation_result"] = result
        st.session_state["shift_generation_elapsed"] = elapsed

    result = st.session_state.get("shift_generation_result")
    if result is None:
        return

    elapsed = st.session_state.get("shift_generation_elapsed", 0.0)
    status = result["status"]

    if result["schedule"] is None:
        st.error(f"シフト生成不可（status={status}, 所要時間={elapsed:.1f}秒）")
        calendar_days = calendar.expand_month(config, monthly)

        st.subheader("要因の手がかり（休暇集中日）")
        vacation_hints = compute_vacation_concentration_hints(calendar_days, monthly.vacations)
        if vacation_hints:
            st.dataframe(
                [
                    {
                        "date": h.date,
                        "weekday": h.weekday,
                        "vacation_count": h.vacation_count,
                    }
                    for h in vacation_hints
                ],
                width="stretch",
            )
        else:
            st.caption("休暇の集中は検出されませんでした。")

        st.subheader("要因の手がかり（必要人数と配置可能人数の差）")
        deficit_hints = compute_headcount_deficit_hints(config, calendar_days, monthly.vacations)
        if deficit_hints:
            st.dataframe(
                [
                    {
                        "date": h.date,
                        "weekday": h.weekday,
                        "area": h.area,
                        "time": f"{h.window_start}-{h.window_end}",
                        "required": h.required_headcount,
                        "available": h.available_count,
                        "deficit": h.deficit,
                    }
                    for h in deficit_hints
                ],
                width="stretch",
            )
        else:
            st.caption("必要人数の不足は検出されませんでした（他の制約が要因の可能性があります）。")
        return

    st.success(f"シフト生成完了（status={status}, 所要時間={elapsed:.1f}秒）")
    calendar_days = calendar.expand_month(config, monthly)
    rows = build_rows(result["schedule"], calendar_days)
    st.dataframe(rows, width="stretch")

    if config.weekly_hours_check.enabled:
        warnings = validate_hard_constraints(
            config, calendar_days, monthly.vacations, result["schedule"]
        )
        weekly_hours_warnings = [w for w in warnings if w.kind == "sc003_weekly_hours_over"]
        st.subheader("週40時間超過警告（SC-003）")
        if weekly_hours_warnings:
            st.warning(f"{len(weekly_hours_warnings)} 件の週40時間超過があります。")
            st.dataframe(
                [
                    {"スタッフ": w.staff_name or "-", "内容": w.detail}
                    for w in weekly_hours_warnings
                ],
                width="stretch",
            )
        else:
            st.success("週40時間超過はありません。")


render()
