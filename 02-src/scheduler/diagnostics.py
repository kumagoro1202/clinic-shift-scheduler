"""シフト生成結果の品質観察用ユーティリティ（P6-8）。

`internal/engine-design.md` 3.1節で申し送られている「最小配置トークン」
（HC-007〈空出勤防止〉を満たすための必要最小限・1スロットのみの配置で
当日の出勤を成立させる、実質的な意味の薄い配置）の発生頻度を定量的に
観察するために使う。SC-004＋HC-007の組み合わせによる既知の構造的副作用
であり、P6-8で重みプリセットを再調整する際にこの挙動が悪化していないかを
確認する目的で使用する（P6-6/P6-7からの申し送り事項）。
"""

from __future__ import annotations

from .config_loader import parse_time


def minimal_placement_token_stats(
    schedule: dict,
    day_types: dict[str, str],
    slot_minutes: int,
) -> dict:
    """日毎スケジュールから「最小配置トークン」の発生頻度を集計する。

    「最小配置トークン」は、当日の配置合計時間が1スロット（`slot_minutes`）
    以下（HC-007が要求する最低限）であることをもって判定する。

    Args:
        schedule: `engine.run()` / `engine.run_monthly()` が返す
            `result["schedule"]`（日キー→スタッフ名→配置情報）。
        day_types: 日キー（曜日 or 日付）から day_type を引く辞書。
        slot_minutes: スロット解像度（分）。

    Returns:
        以下のキーを持つ集計結果:
        - total_workdays: 出勤日数の総数（全スタッフ・全日の合計）
        - minimal_tokens: 最小配置トークンの件数（全日種別合計）
        - half_day_workdays: 半日診療日における出勤日数の総数
        - half_day_minimal_tokens: 半日診療日における最小配置トークンの件数
        - half_day_ratio: `half_day_minimal_tokens / half_day_workdays`
          （半日診療日の出勤が1日も無ければ 0.0）
        - per_staff: スタッフ名→最小配置トークン件数（全日種別合計）
    """
    total_workdays = 0
    minimal_tokens = 0
    half_day_workdays = 0
    half_day_minimal_tokens = 0
    per_staff: dict[str, int] = {}

    for day_key, day_schedule in schedule.items():
        day_type = day_types.get(day_key)
        for staff_name, entry in day_schedule.items():
            total_workdays += 1
            assigned_minutes = sum(
                parse_time(segment["end"]) - parse_time(segment["start"])
                for segment in entry["work"]
            )
            is_minimal = assigned_minutes <= slot_minutes

            if day_type == "half":
                half_day_workdays += 1
                if is_minimal:
                    half_day_minimal_tokens += 1

            if is_minimal:
                minimal_tokens += 1
                per_staff[staff_name] = per_staff.get(staff_name, 0) + 1

    half_day_ratio = (
        half_day_minimal_tokens / half_day_workdays if half_day_workdays else 0.0
    )

    return {
        "total_workdays": total_workdays,
        "minimal_tokens": minimal_tokens,
        "half_day_workdays": half_day_workdays,
        "half_day_minimal_tokens": half_day_minimal_tokens,
        "half_day_ratio": half_day_ratio,
        "per_staff": per_staff,
    }
