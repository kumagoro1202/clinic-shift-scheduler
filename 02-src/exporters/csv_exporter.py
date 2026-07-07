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
