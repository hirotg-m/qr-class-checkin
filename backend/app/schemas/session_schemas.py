from __future__ import annotations

from pydantic import BaseModel

from app.schemas.schedule_schemas import ScheduleResponse


class ParticipantView(BaseModel):
    participantId: str
    name: str
    grade: str
    isNew: bool
    checkedInAt: str
    inputBy: str
    visitCount: int
    previousDate: str | None = None


class SessionResponse(BaseModel):
    date: str
    schedule: ScheduleResponse | None
    participants: list[ParticipantView]
