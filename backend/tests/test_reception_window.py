from __future__ import annotations

from datetime import datetime

from app.domain.reception_window import ScheduleEntry, is_accepting_now

SCHEDULE = ScheduleEntry(date="2026-07-07", start_time="16:00", end_time="17:00")


def test_accepting_within_window():
    now = datetime(2026, 7, 7, 15, 45)  # 開始15分前
    assert is_accepting_now(SCHEDULE, now) is True


def test_accepting_exactly_at_open_boundary():
    now = datetime(2026, 7, 7, 15, 30)  # 開始30分前ちょうど
    assert is_accepting_now(SCHEDULE, now) is True


def test_not_accepting_before_window():
    now = datetime(2026, 7, 7, 15, 20)  # 開始40分前
    assert is_accepting_now(SCHEDULE, now) is False


def test_accepting_exactly_at_end_boundary():
    now = datetime(2026, 7, 7, 17, 0)
    assert is_accepting_now(SCHEDULE, now) is True


def test_not_accepting_after_end():
    now = datetime(2026, 7, 7, 17, 1)
    assert is_accepting_now(SCHEDULE, now) is False


def test_none_schedule_never_accepting():
    assert is_accepting_now(None, datetime(2026, 7, 7, 16, 0)) is False
