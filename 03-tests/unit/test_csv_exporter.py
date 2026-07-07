"""P6-9 CSV出力（exporters/csv_exporter.py）のテスト。

`external/output-design.md` 3章の仕様（ロング形式・列順序・休憩行・
UTF-8 BOM付き・CRLF改行）を検証する。スケジュール結果は本テスト用に
構築した最小データを使用し、実在データは使用しない。
"""

from pathlib import Path

from exporters.csv_exporter import CSV_HEADER, build_rows, rows_to_schedule, write_csv
from scheduler.calendar import CalendarDay

_CALENDAR_DAYS = (
    CalendarDay(date="2026-08-03", weekday="mon", day_type="full"),
    CalendarDay(date="2026-08-04", weekday="tue", day_type="full"),
)

_SCHEDULE = {
    "2026-08-03": {
        "スタッフA": {
            "pattern": "early",
            "work": [
                {"area": "reception", "start": "08:30", "end": "12:30"},
                {"area": "reception", "start": "13:30", "end": "17:30"},
            ],
            "break": {"start": "12:30", "end": "13:30"},
        },
        "スタッフB": {
            "pattern": "half",
            "work": [{"area": "rehab", "start": "08:30", "end": "13:30"}],
            "break": None,
        },
    },
    "2026-08-04": {},
}


def test_build_rows_orders_by_date_then_staff():
    rows = build_rows(_SCHEDULE, _CALENDAR_DAYS)
    assert [r["staff"] for r in rows[:3]] == ["スタッフA", "スタッフA", "スタッフA"]
    assert rows[3]["staff"] == "スタッフB"


def test_build_rows_break_row_placed_in_time_order():
    """休憩行が area='break' として勤務セグメントと開始時刻順に並ぶこと。"""
    rows = build_rows(_SCHEDULE, _CALENDAR_DAYS)
    staff_a_rows = [r for r in rows if r["staff"] == "スタッフA"]
    assert [(r["area"], r["start"], r["end"]) for r in staff_a_rows] == [
        ("reception", "08:30", "12:30"),
        ("break", "12:30", "13:30"),
        ("reception", "13:30", "17:30"),
    ]


def test_build_rows_includes_weekday_from_calendar_days():
    rows = build_rows(_SCHEDULE, _CALENDAR_DAYS)
    assert all(r["weekday"] == "mon" for r in rows if r["date"] == "2026-08-03")


def test_build_rows_skips_days_with_no_assignments():
    rows = build_rows(_SCHEDULE, _CALENDAR_DAYS)
    assert all(r["date"] != "2026-08-04" for r in rows)


def test_rows_to_schedule_is_inverse_of_build_rows():
    """P7-5: build_rows で得た行を rows_to_schedule へ渡すと、
    元のスケジュール（休日以外）へ復元できること。"""
    rows = build_rows(_SCHEDULE, _CALENDAR_DAYS)
    rebuilt = rows_to_schedule(rows)
    assert rebuilt == {
        "2026-08-03": {
            "スタッフA": _SCHEDULE["2026-08-03"]["スタッフA"],
            "スタッフB": _SCHEDULE["2026-08-03"]["スタッフB"],
        }
    }


def test_rows_to_schedule_skips_incomplete_rows():
    """編集中の空行（date/staff が未入力）は読み飛ばすこと。"""
    rows = [
        {"date": "", "staff": "", "pattern": "", "area": "", "start": "", "end": ""},
        {
            "date": "2026-08-03",
            "staff": "スタッフA",
            "pattern": "early",
            "area": "reception",
            "start": "08:30",
            "end": "12:30",
        },
    ]
    rebuilt = rows_to_schedule(rows)
    assert list(rebuilt.keys()) == ["2026-08-03"]
    assert rebuilt["2026-08-03"]["スタッフA"]["work"] == [
        {"area": "reception", "start": "08:30", "end": "12:30"}
    ]


def test_write_csv_output_format(tmp_path: Path):
    """UTF-8 BOM付き・CRLF改行・列順序が仕様どおりであること。"""
    output_path = tmp_path / "shift.csv"
    write_csv(_SCHEDULE, _CALENDAR_DAYS, output_path)

    raw = output_path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "UTF-8 BOMが付与されているはずです"

    text = raw.decode("utf-8-sig")
    lines = text.split("\r\n")
    assert lines[0] == ",".join(CSV_HEADER)
    assert lines[1] == "2026-08-03,mon,スタッフA,early,reception,08:30,12:30"
    assert lines[2] == "2026-08-03,mon,スタッフA,early,break,12:30,13:30"
    assert lines[3] == "2026-08-03,mon,スタッフA,early,reception,13:30,17:30"
    assert lines[4] == "2026-08-03,mon,スタッフB,half,rehab,08:30,13:30"
    # 末尾の空行を除き、ヘッダー + 4行のデータ行のみであること
    assert [line for line in lines if line] == lines[:5]
