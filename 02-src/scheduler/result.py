"""シフト結果のデータ型と検証（ハード制約充足チェック）。

`internal/data-model.md` 5 章の設計方針に基づき、生成結果（`scheduler.engine`
の出力形式）と手動編集後の結果（P7-5）を同一の検証関数で扱う（二重実装を
避ける）。検証対象のスケジュール形式は `engine._extract_schedule` の戻り値
と同じ辞書形式（`{日付: {スタッフ名: {"pattern", "work", "break"}}}`）。
"""

from __future__ import annotations

from dataclasses import dataclass

from .calendar import CalendarDay, DateVacation
from .config_loader import AM_PM_BOUNDARY_MINUTES, Config, format_time, parse_time


@dataclass(frozen=True)
class Warning:
    """ハード制約違反（週 40h 超過等の警告もこの型で表現する。data-model.md 5 章）。"""

    kind: str
    staff_name: str | None
    detail: str


def _iso_week_key(date_str: str) -> str:
    from datetime import date

    year, week, _ = date.fromisoformat(date_str).isocalendar()
    return f"{year}-W{week:02d}"


def _vacation_overlaps(kind: str, start: int, end: int) -> bool:
    """HC-004: 休暇によりその時間帯の一部が勤務不可かどうか（constraints.py の
    `_vacation_blocks` のスロット判定を時間帯（start, end）へ一般化したもの）。
    """
    if kind == "full":
        return True
    if kind == "am":
        return start < AM_PM_BOUNDARY_MINUTES
    return end > AM_PM_BOUNDARY_MINUTES  # pm


def validate_hard_constraints(
    config: Config,
    calendar_days: tuple[CalendarDay, ...],
    vacations: tuple[DateVacation, ...],
    schedule: dict,
) -> list[Warning]:
    """スケジュール（生成結果または手動編集後）がハード制約に違反していないかを検証する。

    検証対象: HC-001（必要人数）・HC-002（同一時刻の複数エリア配置）・
    HC-003（パターン時間内・実働時間・休憩・週勤務日数上限）・
    HC-004（休暇時間帯への配置）・配置エリアへのスキル適性。
    強制ブロックはしない設計のため、違反があっても保存自体は呼び出し側の
    判断に委ねる（`external/output-design.md` 2 章）。
    """
    warnings: list[Warning] = []
    weekday_by_date = {d.date: d.weekday for d in calendar_days}
    vacation_lookup = {(v.staff, v.date): v.kind for v in vacations}
    staff_by_name = {s.name: s for s in config.staff}
    area_by_name = {a.name: a for a in config.areas}
    pattern_by_name = {p.name: p for p in config.shift_patterns}

    weekly_workdays: dict[tuple[str, str], int] = {}

    for date_str, day_entries in schedule.items():
        for staff_name, entry in day_entries.items():
            staff = staff_by_name.get(staff_name)
            segments = list(entry.get("work") or [])
            break_range = entry.get("break")
            pattern = pattern_by_name.get(entry.get("pattern"))

            if staff is None or pattern is None:
                continue

            if not segments:
                warnings.append(
                    Warning(
                        "hc007_empty_attendance",
                        staff_name,
                        f"{date_str}: 出勤しているのに配置がありません",
                    )
                )

            if segments or break_range:
                week_key = _iso_week_key(date_str)
                key = (staff_name, week_key)
                weekly_workdays[key] = weekly_workdays.get(key, 0) + 1

            vacation_kind = vacation_lookup.get((staff_name, date_str))
            if vacation_kind == "full" and (segments or break_range):
                warnings.append(
                    Warning(
                        "hc004_vacation_violation",
                        staff_name,
                        f"{date_str}: 終日休暇日に勤務が割り当てられています",
                    )
                )

            all_segments = list(segments)
            if break_range:
                all_segments = [*all_segments, {"area": "break", **break_range}]

            work_minutes = 0
            for seg in segments:
                start = parse_time(seg["start"])
                end = parse_time(seg["end"])
                work_minutes += end - start

                if start < pattern.window.start or end > pattern.window.end:
                    warnings.append(
                        Warning(
                            "hc003_out_of_window",
                            staff_name,
                            f"{date_str}: パターン({pattern.name})の時間外の配置が"
                            f"あります（{seg['area']} {seg['start']}-{seg['end']}）",
                        )
                    )

                if vacation_kind and _vacation_overlaps(vacation_kind, start, end):
                    warnings.append(
                        Warning(
                            "hc004_vacation_violation",
                            staff_name,
                            f"{date_str}: 休暇時間帯への配置があります"
                            f"（{seg['area']} {seg['start']}-{seg['end']}）",
                        )
                    )

                area = area_by_name.get(seg["area"])
                if area is not None and not staff.qualifies(area):
                    warnings.append(
                        Warning(
                            "unqualified_area",
                            staff_name,
                            f"{date_str}: スキル不足のエリアへの配置です（{area.name}）",
                        )
                    )

            if work_minutes > pattern.working_minutes:
                warnings.append(
                    Warning(
                        "hc003_over_working_minutes",
                        staff_name,
                        f"{date_str}: 実働時間がパターン上限"
                        f"（{pattern.working_minutes}分）を超えています",
                    )
                )

            if pattern.break_minutes > 0 and not break_range:
                warnings.append(
                    Warning(
                        "hc003_missing_break",
                        staff_name,
                        f"{date_str}: 休憩が設定されていません",
                    )
                )
            elif break_range:
                b_start = parse_time(break_range["start"])
                b_end = parse_time(break_range["end"])
                if (b_end - b_start) != pattern.break_minutes:
                    warnings.append(
                        Warning(
                            "hc003_break_duration",
                            staff_name,
                            f"{date_str}: 休憩時間がパターン既定"
                            f"（{pattern.break_minutes}分）と一致しません",
                        )
                    )

            sorted_segments = sorted(all_segments, key=lambda s: parse_time(s["start"]))
            for prev, curr in zip(sorted_segments, sorted_segments[1:]):
                if parse_time(curr["start"]) < parse_time(prev["end"]):
                    warnings.append(
                        Warning(
                            "hc002_overlap",
                            staff_name,
                            f"{date_str}: 時間帯が重複しています"
                            f"（{prev['area']} {prev['start']}-{prev['end']} / "
                            f"{curr['area']} {curr['start']}-{curr['end']}）",
                        )
                    )

    for date_str, day_entries in schedule.items():
        weekday = weekday_by_date.get(date_str)
        if weekday is None:
            continue
        for area in config.areas:
            for band in area.requirements[weekday]:
                covered = 0
                for entry in day_entries.values():
                    for seg in entry.get("work") or []:
                        if seg["area"] != area.name:
                            continue
                        start = parse_time(seg["start"])
                        end = parse_time(seg["end"])
                        if start < band.window.end and end > band.window.start:
                            covered += 1
                            break
                if covered < band.headcount:
                    warnings.append(
                        Warning(
                            "hc001_understaffed",
                            None,
                            f"{date_str} {area.name} "
                            f"{format_time(band.window.start)}-{format_time(band.window.end)}: "
                            f"必要人数 {band.headcount} 名に対し {covered} 名です",
                        )
                    )

    for (staff_name, week_key), count in weekly_workdays.items():
        staff = staff_by_name.get(staff_name)
        if staff is not None and count > staff.weekly_workdays:
            warnings.append(
                Warning(
                    "hc003_over_weekly_workdays",
                    staff_name,
                    f"{week_key}: 週勤務日数が上限（{staff.weekly_workdays}日）"
                    f"を超えています（{count}日）",
                )
            )

    return warnings
