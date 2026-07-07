"""ui/pages/staff_management.py（P7-2）の AppTest による表示・保存動作確認。

ARCHITECTURE.md 4 章のテスト戦略（UI 層は Streamlit AppTest でヘッドレス検証）に
基づく。データソースは環境変数 CLINIC_STAFF_PATH でテスト用の一時ファイルへ
差し替える（ファイルパス方式の st.Page はページ再実行のたびにスクリプトを
再読込するため、Python オブジェクトの直接差し替えができない）。
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE_PATH = REPO_ROOT / "02-src" / "ui" / "pages" / "staff_management.py"
SAMPLE_STAFF_PATH = REPO_ROOT / "config" / "samples" / "sample_staff.yaml"


@pytest.fixture
def staff_yaml_copy(tmp_path, monkeypatch):
    target = tmp_path / "staff.yaml"
    shutil.copy(SAMPLE_STAFF_PATH, target)
    monkeypatch.setenv("CLINIC_STAFF_PATH", str(target))
    return target


def test_staff_management_shows_title_and_editor(staff_yaml_copy):
    at = AppTest.from_file(str(PAGE_PATH))
    at.run(timeout=15)
    assert not at.exception
    assert at.title[0].value == "スタッフ管理"
    assert at.caption[0].value.startswith("スタッフマスタ")
    assert at.button[0].label == "保存"


def test_staff_management_save_button_persists_rows(staff_yaml_copy):
    at = AppTest.from_file(str(PAGE_PATH))
    at.run(timeout=15)

    at.button[0].click().run(timeout=15)

    assert not at.exception
    assert at.success
    assert "保存しました" in at.success[0].value
    assert "スタッフA" in staff_yaml_copy.read_text(encoding="utf-8")


def test_staff_management_shows_error_for_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("CLINIC_STAFF_PATH", str(tmp_path / "does_not_exist.yaml"))

    at = AppTest.from_file(str(PAGE_PATH))
    at.run(timeout=15)

    assert not at.exception
    assert at.error
    assert "読込に失敗" in at.error[0].value
