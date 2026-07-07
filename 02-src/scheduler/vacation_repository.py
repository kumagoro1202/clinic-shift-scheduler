"""月次入力ファイル（schedule-YYYYMM.yaml, schema_version: 2）の
休暇データ（vacations）の読込・保存。

external/input-design.md 5 章のスキーマ・6 章の検証ルール（V-10〜V-12）に
基づく。管理者 UI（P7-3, FR-02）からの休暇入力はこのモジュールを経由する。
`calendar_overrides` 等の他フィールドはそのまま保持し、休暇入力画面からは
変更しない（round trip）。
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import yaml

SUPPORTED_SCHEMA_VERSION = 2
VACATION_KINDS = ("full", "am", "pm")


class VacationValidationError(ValueError):
    """月次休暇入力の内容が不正な場合に送出する。"""


def _month_dates(target_month: str) -> set[str]:
    try:
        year_str, month_str = target_month.split("-")
        year, month = int(year_str), int(month_str)
    except ValueError as exc:
        raise VacationValidationError(
            f"target_month の形式が不正です: {target_month!r}"
        ) from exc
    if not 1 <= month <= 12:
        raise VacationValidationError(f"target_month の月が不正です: {target_month!r}")
    first_day = date(year, month, 1)
    next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    dates = set()
    current = first_day
    while current < next_month:
        dates.add(current.isoformat())
        current += timedelta(days=1)
    return dates


def _validate_row(
    row: dict,
    index: int,
    valid_dates: set[str],
    staff_names: set[str],
    seen: set[tuple[str, str]],
) -> list[str]:
    errors = []
    prefix = f"{index + 1} 行目"

    staff = row.get("staff")
    if not isinstance(staff, str) or not staff.strip():
        errors.append(f"{prefix}: スタッフが未選択です")
    elif staff not in staff_names:
        errors.append(f"{prefix}: スタッフマスタに存在しません: {staff!r}")

    vacation_date = row.get("date")
    if not isinstance(vacation_date, str) or vacation_date not in valid_dates:
        errors.append(f"{prefix}: 休暇日が対象月内の日付ではありません: {vacation_date!r}")

    kind = row.get("kind")
    if kind not in VACATION_KINDS:
        errors.append(
            f"{prefix}: 休暇種別が不正です: {kind!r}（対応値: {VACATION_KINDS}）"
        )

    if isinstance(staff, str) and isinstance(vacation_date, str):
        key = (staff, vacation_date)
        if key in seen:
            errors.append(
                f"{prefix}: 同一スタッフ・同一日の休暇が重複しています: {staff} {vacation_date}"
            )
        else:
            seen.add(key)

    return errors


def _validate_rows(rows: list[dict], target_month: str, staff_names: set[str]) -> None:
    valid_dates = _month_dates(target_month)
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(rows):
        errors.extend(_validate_row(row, index, valid_dates, staff_names, seen))
    if errors:
        raise VacationValidationError("; ".join(errors))


def load_schedule(path: str | Path) -> dict:
    """月次入力ファイルを読み込み、休暇編集画面向けの構造を返す。

    戻り値は {"target_month", "vacations", "raw"}。"raw" は
    calendar_overrides 等を含む元データそのもので、保存時にそのまま
    引き継ぐために保持する。
    """
    path = Path(path)
    if not path.is_file():
        raise VacationValidationError(f"月次設定ファイルが見つかりません: {path}")
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise VacationValidationError(
            "月次設定ファイルのトップレベルはマッピングである必要があります"
        )

    version = raw.get("schema_version")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise VacationValidationError(
            f"schema_version {version!r} は未対応です"
            f"（対応バージョン: {SUPPORTED_SCHEMA_VERSION}）"
        )

    target_month = raw.get("target_month")
    if not isinstance(target_month, str):
        raise VacationValidationError("target_month が未設定です")

    rows = []
    for entry in raw.get("vacations") or []:
        rows.append(
            {
                "staff": entry.get("staff"),
                "date": entry.get("date"),
                "kind": entry.get("kind"),
                "paid": bool(entry.get("paid", False)),
            }
        )

    return {"target_month": target_month, "vacations": rows, "raw": raw}


def save_schedule(
    path: str | Path,
    target_month: str,
    vacation_rows: list[dict],
    raw: dict,
    staff_names: list[str],
) -> None:
    """休暇行を検証し、月次入力ファイルへ保存する。

    `raw`（読込時に取得した元データ）の `calendar_overrides` 等は保持し、
    `vacations` のみを差し替える。不正な内容の場合は
    VacationValidationError を送出し、ファイルは変更しない。
    """
    vacation_rows = [dict(row) for row in vacation_rows]
    _validate_rows(vacation_rows, target_month, set(staff_names))

    vacation_entries = []
    for row in vacation_rows:
        vacation_entries.append(
            {
                "staff": row["staff"],
                "date": row["date"],
                "kind": row["kind"],
                "paid": bool(row.get("paid", False)),
            }
        )

    document = dict(raw)
    document["schema_version"] = SUPPORTED_SCHEMA_VERSION
    document["target_month"] = target_month
    document["vacations"] = vacation_entries

    path = Path(path)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(document, f, allow_unicode=True, sort_keys=False)
