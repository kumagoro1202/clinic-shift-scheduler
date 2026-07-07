"""シフト生成 CLI（バッチ実行・動作確認用）。

設定ファイル・月次入力ファイルを指定して1ヶ月分のシフトを生成し、
CSV形式で出力する（P6-9）。

使用例:
    python cli.py generate \\
        --config config/samples/sample_clinic.yaml \\
        --schedule config/samples/sample_schedule_202608.yaml \\
        --output shift_202608.csv
"""

from __future__ import annotations

import argparse
import sys
import time

from exporters.csv_exporter import write_csv
from scheduler import calendar, config_loader, engine

# ARCHITECTURE.md 7章 P6-9の性能要件（1ヶ月分の生成が60秒以内に完了すること）は
# CLI全体の所要時間（設定読込・求解・CSV書き出しの合計）を指す。求解自体に60秒
# 丸ごと使うと、求解タイムアウト超過分やCSV書き出し等のオーバーヘッドで合計が
# 60秒を超えうるため、既定値には余裕を持たせる。
DEFAULT_TIME_LIMIT_SECONDS = 55.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli",
        description="設定ファイルを指定して1ヶ月分のシフトを生成しCSV出力する",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="シフトを生成しCSV出力する")
    generate.add_argument("--config", required=True, help="診療所設定ファイル（YAML）")
    generate.add_argument("--schedule", required=True, help="月次入力ファイル（YAML）")
    generate.add_argument("--output", required=True, help="CSV出力先パス")
    generate.add_argument(
        "--time-limit",
        type=float,
        default=DEFAULT_TIME_LIMIT_SECONDS,
        help=f"求解タイムリミット（秒。既定値: {DEFAULT_TIME_LIMIT_SECONDS}）",
    )
    return parser


def run_generate(
    config_path: str, schedule_path: str, output_path: str, time_limit_seconds: float
) -> int:
    """1ヶ月分のシフトを生成しCSV出力する。生成不可の場合は非ゼロを返す。"""
    config = config_loader.load_config(config_path)
    monthly = calendar.load_monthly_schedule(schedule_path, config)
    calendar_days = calendar.expand_month(config, monthly)

    started = time.monotonic()
    result = engine.run_monthly(config, schedule_path, time_limit_seconds=time_limit_seconds)
    elapsed = time.monotonic() - started

    if result["schedule"] is None:
        print(
            f"シフト生成不可（status={result['status']}, 所要時間={elapsed:.1f}秒）",
            file=sys.stderr,
        )
        return 1

    write_csv(result["schedule"], calendar_days, output_path)
    print(
        f"シフト生成完了（status={result['status']}, 対象月={monthly.target_month}, "
        f"所要時間={elapsed:.1f}秒）→ {output_path}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "generate":
        return run_generate(args.config, args.schedule, args.output, args.time_limit)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
