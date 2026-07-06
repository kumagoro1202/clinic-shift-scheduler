"""P6-9 シフト生成CLI・CSV出力（cli.py）のテスト。

テスト専用のサンプル設定（config/samples/sample_clinic.yaml・
config/samples/sample_schedule_202608.yaml）と、本テスト専用の最小構成
設定（敵対的検証用）のみを使用する。実在データは使用しない。

■ 性能要件（MANDATORY・ARCHITECTURE.md 7章 P6-9）
1ヶ月分のシフト生成が60秒以内に完了することを検証する
（test_run_generate_completes_within_60_seconds）。
"""

import time
from pathlib import Path

import pytest

import cli

SAMPLE_CONFIG = (
    Path(__file__).resolve().parents[2] / "config" / "samples" / "sample_clinic.yaml"
)
SAMPLE_SCHEDULE = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "samples"
    / "sample_schedule_202608.yaml"
)

PERFORMANCE_LIMIT_SECONDS = 60.0

# 敵対的検証用: 1名構成・平日1日のみ営業だが必要人数2（配置可能な人数を
# 上回る）ため、必ずINFEASIBLEになる最小構成。
_INFEASIBLE_CONFIG_YAML = """
schema_version: 1
work_rules:
  binding_hours: 2
  break_minutes: 0
  working_hours: 2
  break_window: { start: "09:00", end: "09:30" }
slot_minutes: 30
day_types:
  mon: full
  tue: closed
  wed: closed
  thu: closed
  fri: closed
  sat: closed
  sun: closed
shift_patterns:
  - name: day
    day_types: [full]
    start: "09:00"
    end: "10:00"
    break_minutes: 0
areas:
  - name: area_a
    required_skills: [area_a]
    requirements:
      mon:
        - { start: "09:00", end: "09:30", headcount: 2 }
      tue: []
      wed: []
      thu: []
      fri: []
      sat: []
      sun: []
staff:
  - name: "スタッフX"
    employment: full_time
    weekly_workdays: 5
    skills: { area_a: 100 }
    vacations: []
"""

_INFEASIBLE_SCHEDULE_YAML = """
schema_version: 2
target_month: "2026-08"
"""


@pytest.fixture
def infeasible_config_path(tmp_path: Path) -> Path:
    path = tmp_path / "infeasible_config.yaml"
    path.write_text(_INFEASIBLE_CONFIG_YAML, encoding="utf-8")
    return path


@pytest.fixture
def infeasible_schedule_path(tmp_path: Path) -> Path:
    path = tmp_path / "infeasible_schedule.yaml"
    path.write_text(_INFEASIBLE_SCHEDULE_YAML, encoding="utf-8")
    return path


# --- 動作確認（E2E: 設定ファイル指定 → CSV出力） -------------------------------


def test_run_generate_writes_csv_and_returns_zero(tmp_path: Path):
    output_path = tmp_path / "shift_202608.csv"
    exit_code = cli.run_generate(
        str(SAMPLE_CONFIG), str(SAMPLE_SCHEDULE), str(output_path), 60.0
    )
    assert exit_code == 0
    assert output_path.is_file()

    raw = output_path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    lines = [line for line in text.split("\r\n") if line]
    assert lines[0] == "date,weekday,staff,pattern,area,start,end"
    assert len(lines) > 1, "サンプルデータではシフトが1件以上生成されるはずです"
    # 祝日・臨時休診・日曜(2026-08-11/14/02等)は出力に含まれないこと
    assert not any(line.startswith("2026-08-11,") for line in lines)
    assert not any(line.startswith("2026-08-14,") for line in lines)
    assert not any(line.startswith("2026-08-02,") for line in lines)


def test_main_generate_subcommand_end_to_end(tmp_path: Path, capsys):
    output_path = tmp_path / "shift.csv"
    exit_code = cli.main(
        [
            "generate",
            "--config",
            str(SAMPLE_CONFIG),
            "--schedule",
            str(SAMPLE_SCHEDULE),
            "--output",
            str(output_path),
            "--time-limit",
            "60",
        ]
    )
    assert exit_code == 0
    assert output_path.is_file()
    out = capsys.readouterr().out
    assert "シフト生成完了" in out
    assert "2026-08" in out


# --- 性能要件（MANDATORY） -----------------------------------------------------


def test_run_generate_completes_within_60_seconds(tmp_path: Path):
    output_path = tmp_path / "shift_perf.csv"
    started = time.monotonic()
    exit_code = cli.run_generate(
        str(SAMPLE_CONFIG),
        str(SAMPLE_SCHEDULE),
        str(output_path),
        PERFORMANCE_LIMIT_SECONDS,
    )
    elapsed = time.monotonic() - started
    assert exit_code == 0
    assert elapsed <= PERFORMANCE_LIMIT_SECONDS, (
        f"1ヶ月分のシフト生成が性能要件({PERFORMANCE_LIMIT_SECONDS}秒)を"
        f"超過しました: 実測 {elapsed:.1f}秒"
    )


# --- 敵対的検証 ----------------------------------------------------------------


def test_run_generate_infeasible_returns_nonzero_and_no_csv(
    infeasible_config_path: Path, infeasible_schedule_path: Path, tmp_path: Path, capsys
):
    """生成不可(INFEASIBLE)の場合、非ゼロを返しCSVファイルを書き出さないこと。"""
    output_path = tmp_path / "should_not_exist.csv"
    exit_code = cli.run_generate(
        str(infeasible_config_path), str(infeasible_schedule_path), str(output_path), 5.0
    )
    assert exit_code == 1
    assert not output_path.exists()
    err = capsys.readouterr().err
    assert "INFEASIBLE" in err


def test_main_requires_config_and_schedule_arguments():
    """必須引数(--config/--schedule/--output)が欠けている場合はargparseがエラー終了すること。"""
    with pytest.raises(SystemExit):
        cli.main(["generate", "--config", "dummy.yaml"])


def test_main_unknown_config_path_raises_config_error(tmp_path: Path):
    missing_path = tmp_path / "does_not_exist.yaml"
    with pytest.raises(Exception):  # ConfigError（scheduler.config_loader）
        cli.run_generate(
            str(missing_path), str(SAMPLE_SCHEDULE), str(tmp_path / "out.csv"), 5.0
        )
