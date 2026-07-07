"""CSV 出力（P6-9）。

`external/output-design.md` 3 章の仕様に基づき、1 行 = 1 配置セグメント
（同一スタッフ・同一日・同一エリアの連続時間帯）のロング形式で出力する。
文字コードは UTF-8（BOM 付き）、改行は CRLF とする。
"""

from __future__ import annotations

import csv
from pathlib import Path

from scheduler.calendar import CalendarDay

CSV_HEADER = ("date", "weekday", "staff", "pattern", "area", "start", "end")


def build_rows(schedule: dict, calendar_days: tuple[CalendarDay, ...]) -> list[dict]:
    """スケジュール結果をCSV行（辞書のリスト）へ変換する。

    休憩は `area` = "break" の行として、勤務セグメントと開始時刻順に並べる。
    """
    weekday_by_date = {day.date: day.weekday for day in calendar_days}
    rows: list[dict] = []
    for date_str in sorted(schedule.keys()):
        weekday = weekday_by_date.get(date_str, "")
        day_schedule = schedule[date_str]
        for staff_name in sorted(day_schedule.keys()):
            entry = day_schedule[staff_name]
            segments = list(entry["work"])
            if entry.get("break"):
                segments = [*segments, {"area": "break", **entry["break"]}]
            segments.sort(key=lambda seg: seg["start"])
            for segment in segments:
                rows.append(
                    {
                        "date": date_str,
                        "weekday": weekday,
                        "staff": staff_name,
                        "pattern": entry["pattern"],
                        "area": segment["area"],
                        "start": segment["start"],
                        "end": segment["end"],
                    }
                )
    return rows


def rows_to_schedule(rows: list[dict]) -> dict:
    """`build_rows` の逆変換。編集後の行（辞書のリスト）からスケジュール結果
    （`{日付: {スタッフ名: {"pattern", "work", "break"}}}`）を再構築する（P7-5）。

    `area` = "break" の行は休憩として扱う。必須項目（staff/area/start/end）が
    欠けている行（編集途中の空行等）は読み飛ばす。
    """
    schedule: dict[str, dict[str, dict]] = {}
    for row in rows:
        date_str = row.get("date")
        staff_name = row.get("staff")
        if not date_str or not staff_name:
            continue
        entry = schedule.setdefault(date_str, {}).setdefault(
            staff_name, {"pattern": row.get("pattern"), "work": [], "break": None}
        )
        if row.get("pattern"):
            entry["pattern"] = row["pattern"]

        area, start, end = row.get("area"), row.get("start"), row.get("end")
        if not area or not start or not end:
            continue
        if area == "break":
            entry["break"] = {"start": start, "end": end}
        else:
            entry["work"].append({"area": area, "start": start, "end": end})
    return schedule


def write_csv(
    schedule: dict, calendar_days: tuple[CalendarDay, ...], output_path: str | Path
) -> None:
    """スケジュール結果をCSVファイルへ書き出す（UTF-8 BOM付き・CRLF改行）。"""
    rows = build_rows(schedule, calendar_days)
    output_path = Path(output_path)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, lineterminator="\r\n")
        writer.writerow(CSV_HEADER)
        for row in rows:
            writer.writerow([row[column] for column in CSV_HEADER])
