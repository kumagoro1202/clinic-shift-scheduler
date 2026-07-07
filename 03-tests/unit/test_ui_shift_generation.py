"""ui/pages/shift_generation.py（P7-4）の AppTest による表示・生成動作確認。

ARCHITECTURE.md 4 章のテスト戦略（UI 層は Streamlit AppTest でヘッドレス検証）に
基づく。データソースは環境変数 CLINIC_CONFIG_PATH / CLINIC_SCHEDULE_PATH で
テスト用の一時ファイルへ差し替える（vacation_input.py と同様の理由で
ファイルパス方式の st.Page は Python オブジェクトの直接差し替えができない）。
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE_PATH = REPO_ROOT / "02-src" / "ui" / "pages" / "shift_generation.py"
SAMPLE_CONFIG_PATH = REPO_ROOT / "config" / "samples" / "sample_clinic.yaml"
SAMPLE_SCHEDULE_PATH = REPO_ROOT / "config" / "samples" / "sample_schedule_202608.yaml"

# 2026-08-03（月）に、リハ室配置可能な全スタッフ（A・C・D）を終日休暇にし、
# 意図的に INFEASIBLE（rehab 必要人数 1 に対し配置可能 0）を発生させる。
INFEASIBLE_SCHEDULE_YAML = """
schema_version: 2
target_month: "2026-08"
vacations:
  - { staff: "スタッフA", date: "2026-08-03", kind: full }
  - { staff: "スタッフC", date: "2026-08-03", kind: full }
  - { staff: "スタッフD", date: "2026-08-03", kind: full }
"""


@pytest.fixture
def feasible_env(tmp_path, monkeypatch):
    config_target = tmp_path / "clinic.yaml"
    shutil.copy(SAMPLE_CONFIG_PATH, config_target)
    monkeypatch.setenv("CLINIC_CONFIG_PATH", str(config_target))

    schedule_target = tmp_path / "schedule.yaml"
    shutil.copy(SAMPLE_SCHEDULE_PATH, schedule_target)
    monkeypatch.setenv("CLINIC_SCHEDULE_PATH", str(schedule_target))
    return schedule_target


@pytest.fixture
def infeasible_env(tmp_path, monkeypatch):
    config_target = tmp_path / "clinic.yaml"
    shutil.copy(SAMPLE_CONFIG_PATH, config_target)
    monkeypatch.setenv("CLINIC_CONFIG_PATH", str(config_target))

    schedule_target = tmp_path / "schedule.yaml"
    schedule_target.write_text(INFEASIBLE_SCHEDULE_YAML, encoding="utf-8")
    monkeypatch.setenv("CLINIC_SCHEDULE_PATH", str(schedule_target))
    return schedule_target


def test_shift_generation_shows_title_and_controls(feasible_env):
    at = AppTest.from_file(str(PAGE_PATH))
    at.run(timeout=15)

    assert not at.exception
    assert at.title[0].value == "シフト生成"
    assert "対象月・最適化モードを指定" in at.caption[0].value
    assert "対象月: 2026-08" in at.text[0].value
    assert at.button[0].label == "生成実行"
    assert at.selectbox[0].value == "balance"


def test_shift_generation_feasible_shows_result_table(feasible_env):
    at = AppTest.from_file(str(PAGE_PATH))
    at.run(timeout=15)

    at.button[0].click().run(timeout=30)

    assert not at.exception
    assert at.success
    assert "生成完了" in at.success[0].value
    assert "status=OPTIMAL" in at.success[0].value or "status=FEASIBLE" in at.success[0].value

    result_rows = at.dataframe[0].value
    assert set(result_rows.columns) == {
        "date",
        "weekday",
        "staff",
        "pattern",
        "area",
        "start",
        "end",
    }
    assert len(result_rows) > 0
    # 祝日・臨時休診（P7-3 のカレンダー例外）は結果に含まれない
    assert "2026-08-11" not in set(result_rows["date"])
    assert "2026-08-14" not in set(result_rows["date"])


def test_shift_generation_infeasible_shows_hints(infeasible_env):
    at = AppTest.from_file(str(PAGE_PATH))
    at.run(timeout=15)

    at.button[0].click().run(timeout=30)

    assert not at.exception
    assert at.error
    assert "生成不可" in at.error[0].value
    assert "status=INFEASIBLE" in at.error[0].value

    # 休暇集中日の手がかり
    vacation_hint_rows = at.dataframe[0].value
    assert "2026-08-03" in set(vacation_hint_rows["date"])
    matched = vacation_hint_rows.loc[vacation_hint_rows["date"] == "2026-08-03", "vacation_count"]
    assert int(matched.iloc[0]) == 3

    # 必要人数不足の手がかり（rehab, 2026-08-03）
    deficit_hint_rows = at.dataframe[1].value
    rehab_rows = deficit_hint_rows[
        (deficit_hint_rows["date"] == "2026-08-03") & (deficit_hint_rows["area"] == "rehab")
    ]
    assert len(rehab_rows) > 0
    assert int(rehab_rows.iloc[0]["deficit"]) >= 1


def test_shift_generation_shows_error_for_missing_config_file(tmp_path, monkeypatch):
    monkeypatch.setenv("CLINIC_CONFIG_PATH", str(tmp_path / "does_not_exist.yaml"))
    monkeypatch.setenv("CLINIC_SCHEDULE_PATH", str(SAMPLE_SCHEDULE_PATH))

    at = AppTest.from_file(str(PAGE_PATH))
    at.run(timeout=15)

    assert not at.exception
    assert at.error
    assert "読込に失敗" in at.error[0].value


def test_shift_generation_shows_error_for_missing_schedule_file(tmp_path, monkeypatch):
    monkeypatch.setenv("CLINIC_CONFIG_PATH", str(SAMPLE_CONFIG_PATH))
    monkeypatch.setenv("CLINIC_SCHEDULE_PATH", str(tmp_path / "does_not_exist.yaml"))

    at = AppTest.from_file(str(PAGE_PATH))
    at.run(timeout=15)

    assert not at.exception
    assert at.error
    assert "読込に失敗" in at.error[0].value
