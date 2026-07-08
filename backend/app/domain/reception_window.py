from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

RECEPTION_OPENS_BEFORE = timedelta(minutes=30)


@dataclass(frozen=True)
class ScheduleEntry:
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str  # HH:MM


def _combine(date: str, time_str: str) -> datetime:
    return datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M")


def is_accepting_now(schedule: ScheduleEntry | None, now: datetime) -> bool:
    """REQUIREMENTS.md 3.3節：活動開始30分前〜終了時刻のみ受付可。"""
    if schedule is None:
        return False
    now = now.replace(tzinfo=None)
    start = _combine(schedule.date, schedule.start_time) - RECEPTION_OPENS_BEFORE
    end = _combine(schedule.date, schedule.end_time)
    return start <= now <= end
