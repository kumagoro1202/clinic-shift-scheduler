"""ui/pages/shift_generation.py（P7-4・P7-7）の AppTest による表示・生成動作確認。

ARCHITECTURE.md 4 章のテスト戦略（UI 層は Streamlit AppTest でヘッドレス検証）に
基づく。データソースは環境変数 CLINIC_CONFIG_PATH / CLINIC_SCHEDULE_PATH で
テスト用の一時ファイルへ差し替える（vacation_input.py と同様の理由で
ファイルパス方式の st.Page は Python オブジェクトの直接差し替えができない）。

P7-7 の SC-003（週40時間超過警告）は、生成エンジンを実際に走らせず
（CP-SAT 求解は重い）、P7-5 のテストと同様に `shift_generation_result` を
session_state へ直接セットして描画のみを検証する。
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


@pytest.fixture
def weekly_hours_enabled_env(tmp_path, monkeypatch):
    # sample_clinic.yaml の weekly_hours_check を有効化・上限5時間に縮小した
    # 一時設定（SC-003 の警告表示検証用。5時間は容易に超過させられる値）。
    config_text = SAMPLE_CONFIG_PATH.read_text(encoding="utf-8").replace(
        "enabled: false # 週40時間チェック（初期OFF）\n    limit_hours: 40",
        "enabled: true # SC-003検証用に一時的に有効化\n    limit_hours: 5",
    )
    assert "enabled: true" in config_text, "sample_clinic.yaml のフォーマットが変更された"
    config_target = tmp_path / "clinic.yaml"
    config_target.write_text(config_text, encoding="utf-8")
    monkeypatch.setenv("CLINIC_CONFIG_PATH", str(config_target))

    schedule_target = tmp_path / "schedule.yaml"
    shutil.copy(SAMPLE_SCHEDULE_PATH, schedule_target)
    monkeypatch.setenv("CLINIC_SCHEDULE_PATH", str(schedule_target))
    return schedule_target


# スタッフA・reception 終日勤務（08:30-12:30, 13:30-17:30 = 8h）。上限5hを超過。
_OVER_LIMIT_SCHEDULE = {
    "2026-08-03": {
        "スタッフA": {
            "pattern": "early",
            "work": [
                {"area": "reception", "start": "08:30", "end": "12:30"},
                {"area": "reception", "start": "13:30", "end": "17:30"},
            ],
            "break": {"start": "12:30", "end": "13:30"},
        },
    },
}

# スタッフA・reception 午前のみ（08:30-12:30 = 4h）。上限5h以内。
_WITHIN_LIMIT_SCHEDULE = {
    "2026-08-03": {
        "スタッフA": {
            "pattern": "early",
            "work": [{"area": "reception", "start": "08:30", "end": "12:30"}],
            "break": None,
        },
    },
}


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

    # CI の共有ランナーは遅く、OR-Tools の求解（時間上限は engine 側で
    # DEFAULT_TIME_LIMIT_SECONDS=55秒）に加えて AppTest の再実行分の余裕を見込む。
    at.button[0].click().run(timeout=90)

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

    # CI の共有ランナーは遅く、OR-Tools の求解（時間上限は engine 側で
    # DEFAULT_TIME_LIMIT_SECONDS=55秒）に加えて AppTest の再実行分の余裕を見込む。
    at.button[0].click().run(timeout=90)

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


def test_weekly_hours_warning_shown_when_exceeded(weekly_hours_enabled_env):
    at = AppTest.from_file(str(PAGE_PATH))
    at.session_state["shift_generation_result"] = {
        "status": "OPTIMAL",
        "schedule": _OVER_LIMIT_SCHEDULE,
    }
    at.run(timeout=15)

    assert not at.exception
    assert "週40時間超過警告（SC-003）" in [s.value for s in at.subheader]
    assert at.warning
    assert any("週40時間超過があります" in w.value for w in at.warning)
    warning_rows = at.dataframe[-1].value
    assert "スタッフA" in set(warning_rows["スタッフ"])


def test_weekly_hours_no_warning_when_within_limit(weekly_hours_enabled_env):
    at = AppTest.from_file(str(PAGE_PATH))
    at.session_state["shift_generation_result"] = {
        "status": "OPTIMAL",
        "schedule": _WITHIN_LIMIT_SCHEDULE,
    }
    at.run(timeout=15)

    assert not at.exception
    assert "週40時間超過警告（SC-003）" in [s.value for s in at.subheader]
    assert any("週40時間超過はありません" in s.value for s in at.success)


def test_weekly_hours_section_hidden_when_disabled(feasible_env):
    at = AppTest.from_file(str(PAGE_PATH))
    at.session_state["shift_generation_result"] = {
        "status": "OPTIMAL",
        "schedule": _OVER_LIMIT_SCHEDULE,
    }
    at.run(timeout=15)

    assert not at.exception
    assert "週40時間超過警告（SC-003）" not in [s.value for s in at.subheader]
