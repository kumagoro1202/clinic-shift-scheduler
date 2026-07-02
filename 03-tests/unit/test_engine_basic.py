"""バッチ1縦スライスの基本テスト。

テスト専用のサンプル設定（config/samples/sample_clinic.yaml・架空スタッフA〜E）
のみを使用する。実在データは使用しない。
"""

from pathlib import Path

import pytest

from scheduler import config_loader, engine

SAMPLE_CONFIG = (
    Path(__file__).resolve().parents[2] / "config" / "samples" / "sample_clinic.yaml"
)


@pytest.fixture(scope="module")
def config():
    return config_loader.load_config(SAMPLE_CONFIG)


@pytest.fixture(scope="module")
def result(config):
    return engine.run(config, time_limit_seconds=60.0)


def test_config_loader_loads_sample(config):
    """テスト1: sample_clinic.yaml を読み込んで config_loader が正常動作すること。"""
    assert config.work_rules.binding_hours == 9
    assert config.work_rules.break_minutes == 60
    assert config.work_rules.working_hours == 8
    assert config.weekly_hours_check.enabled is False
    assert config.day_types["sun"] == "closed"
    assert {a.name for a in config.areas} == {"rehab", "reception"}
    assert len(config.staff) == 5
    assert {p.name for p in config.shift_patterns} == {"early", "late", "half"}


def test_engine_returns_schedule(result):
    """テスト2: engine.run(config) が解を返すこと（INFEASIBLE でないこと）。"""
    assert result["status"] in ("OPTIMAL", "FEASIBLE")
    assert result["schedule"] is not None
    # 診療日（月〜土）に勤務者が存在する
    for weekday in ("mon", "tue", "wed", "thu", "fri", "sat"):
        assert weekday in result["schedule"]
        assert result["schedule"][weekday], f"{weekday} に勤務者がいません"
    # 休診日（日曜）はスケジュール対象外
    assert "sun" not in result["schedule"]


def _coverage(day_schedule, area_name, minute):
    """その時刻にエリアへ配置されている人数を数える。"""
    count = 0
    for entry in day_schedule.values():
        for segment in entry["work"]:
            if segment["area"] != area_name:
                continue
            start = config_loader.parse_time(segment["start"])
            end = config_loader.parse_time(segment["end"])
            if start <= minute < end:
                count += 1
    return count


def test_headcount_requirements_satisfied(config, result):
    """テスト3: 生成シフトで全エリアの必要人数が満たされていること。"""
    step = config.slot_minutes
    for weekday in config.open_weekdays():
        day_schedule = result["schedule"][weekday]
        for area in config.areas:
            for band in area.requirements[weekday]:
                for minute in range(band.window.start, band.window.end, step):
                    actual = _coverage(day_schedule, area.name, minute)
                    assert actual >= band.headcount, (
                        f"{weekday} {area.name} "
                        f"{config_loader.format_time(minute)} の配置人数 {actual} が "
                        f"必要人数 {band.headcount} を下回っています"
                    )


def test_no_double_assignment(config, result):
    """HC-002: 同一スタッフが同時刻に複数エリアへ配置されていないこと。"""
    step = config.slot_minutes
    for weekday, day_schedule in result["schedule"].items():
        for staff_name, entry in day_schedule.items():
            occupied = set()
            for segment in entry["work"]:
                start = config_loader.parse_time(segment["start"])
                end = config_loader.parse_time(segment["end"])
                for minute in range(start, end, step):
                    assert minute not in occupied, (
                        f"{weekday} {staff_name} が {segment['start']} 前後で"
                        f"複数エリアに同時配置されています"
                    )
                    occupied.add(minute)


def test_work_within_pattern_and_break(config, result):
    """HC-003: 配置が勤務パターン内に収まり、休憩ありパターンでは休憩が確保されること。"""
    patterns = {p.name: p for p in config.shift_patterns}
    window = config.work_rules.break_window
    for weekday, day_schedule in result["schedule"].items():
        for staff_name, entry in day_schedule.items():
            pattern = patterns[entry["pattern"]]
            for segment in entry["work"]:
                start = config_loader.parse_time(segment["start"])
                end = config_loader.parse_time(segment["end"])
                assert pattern.window.start <= start and end <= pattern.window.end, (
                    f"{weekday} {staff_name} の配置がパターン {pattern.name} の"
                    f"勤務時間外です"
                )
            if pattern.break_minutes > 0:
                assert entry["break"] is not None, (
                    f"{weekday} {staff_name} に休憩が割り当てられていません"
                )
                break_start = config_loader.parse_time(entry["break"]["start"])
                break_end = config_loader.parse_time(entry["break"]["end"])
                assert break_end - break_start == config.work_rules.break_minutes
                assert window.start <= break_start and break_end <= window.end
                # 休憩中に配置がないこと
                for segment in entry["work"]:
                    seg_start = config_loader.parse_time(segment["start"])
                    seg_end = config_loader.parse_time(segment["end"])
                    assert seg_end <= break_start or break_end <= seg_start, (
                        f"{weekday} {staff_name} が休憩中に配置されています"
                    )
            else:
                assert entry["break"] is None


def test_vacation_respected(config, result):
    """HC-004: 終日休暇の日に勤務が割り当てられないこと。"""
    for staff in config.staff:
        for vacation in staff.vacations:
            if vacation.kind != "full":
                continue
            day_schedule = result["schedule"].get(vacation.weekday, {})
            assert staff.name not in day_schedule, (
                f"{staff.name} の {vacation.weekday} は終日休暇のはずですが"
                f"勤務が割り当てられています"
            )
