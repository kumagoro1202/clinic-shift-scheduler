"""スタッフマスタ（staff.yaml, schema_version: 2）の読込・保存。

external/input-design.md 4 章のスキーマに基づく。診療所設定（config_loader）
とは独立したファイルとして扱い、管理者 UI（P7-2, FR-01）からの
表示・編集はこのモジュールを経由する。
"""

from __future__ import annotations

from pathlib import Path

import yaml

SUPPORTED_SCHEMA_VERSION = 2

EMPLOYMENT_TYPES = ("full_time", "part_time")

# スキルスコア 4 項目（REQUIREMENTS FR-01・input-design.md 4 章）
SKILL_KEYS = ("rehab", "reception_am", "reception_pm", "general")

MIN_WEEKLY_WORKDAYS = 1
MAX_WEEKLY_WORKDAYS = 7


class StaffValidationError(ValueError):
    """スタッフマスタの内容が不正な場合に送出する。"""


def _validate_row(row: dict, index: int, seen_names: set[str]) -> list[str]:
    errors = []
    prefix = f"{index + 1} 行目"

    name = row.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(f"{prefix}: スタッフ名が未入力です")
    elif name in seen_names:
        errors.append(f"{prefix}: スタッフ名が重複しています: {name!r}")
    else:
        seen_names.add(name)

    employment = row.get("employment")
    if employment not in EMPLOYMENT_TYPES:
        errors.append(
            f"{prefix}: 勤務形態が不正です: {employment!r}（対応値: {EMPLOYMENT_TYPES}）"
        )

    workdays = row.get("weekly_workdays")
    if not isinstance(workdays, int) or isinstance(workdays, bool) or not (
        MIN_WEEKLY_WORKDAYS <= workdays <= MAX_WEEKLY_WORKDAYS
    ):
        errors.append(
            f"{prefix}: 週勤務日数が不正です: {workdays!r}"
            f"（{MIN_WEEKLY_WORKDAYS}〜{MAX_WEEKLY_WORKDAYS} の整数）"
        )

    for key in SKILL_KEYS:
        score = row.get(key)
        if not isinstance(score, int) or isinstance(score, bool) or not (0 <= score <= 100):
            errors.append(f"{prefix}: スキル {key} が 0〜100 の範囲外です: {score!r}")

    return errors


def _validate_rows(rows: list[dict]) -> None:
    errors: list[str] = []
    seen_names: set[str] = set()
    for index, row in enumerate(rows):
        errors.extend(_validate_row(row, index, seen_names))
    if errors:
        raise StaffValidationError("; ".join(errors))


def load_staff(path: str | Path) -> list[dict]:
    """staff.yaml を読み込み、フラット化した行データのリストを返す。

    各行は {"name", "employment", "weekly_workdays", *SKILL_KEYS} を持つ
    フラットな dict（UI の表編集コンポーネント向け）。
    """
    path = Path(path)
    if not path.is_file():
        raise StaffValidationError(f"スタッフマスタファイルが見つかりません: {path}")
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise StaffValidationError("スタッフマスタのトップレベルはマッピングである必要があります")

    version = raw.get("schema_version")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise StaffValidationError(
            f"schema_version {version!r} は未対応です"
            f"（対応バージョン: {SUPPORTED_SCHEMA_VERSION}）"
        )

    rows = []
    for entry in raw.get("staff") or []:
        skills = entry.get("skills") or {}
        row = {
            "name": entry.get("name"),
            "employment": entry.get("employment"),
            "weekly_workdays": entry.get("weekly_workdays"),
        }
        for key in SKILL_KEYS:
            row[key] = skills.get(key)
        rows.append(row)
    return rows


def save_staff(path: str | Path, rows: list[dict]) -> None:
    """行データのリストを検証し、staff.yaml（schema_version: 2）へ保存する。

    不正な内容の場合は StaffValidationError を送出し、ファイルは変更しない。
    """
    rows = [dict(row) for row in rows]
    _validate_rows(rows)

    staff_entries = []
    for row in rows:
        staff_entries.append(
            {
                "name": row["name"],
                "employment": row["employment"],
                "weekly_workdays": row["weekly_workdays"],
                "skills": {key: row[key] for key in SKILL_KEYS},
            }
        )

    document = {"schema_version": SUPPORTED_SCHEMA_VERSION, "staff": staff_entries}
    path = Path(path)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(document, f, allow_unicode=True, sort_keys=False)
