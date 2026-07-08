from __future__ import annotations

from pydantic import BaseModel


class ScheduleCreateRequest(BaseModel):
    date: str
    startTime: str
    endTime: str
    location: str = ""


class ScheduleUpdateRequest(BaseModel):
    startTime: str
    endTime: str
    location: str = ""


class ScheduleResponse(BaseModel):
    date: str
    startTime: str
    endTime: str
    location: str


class PinSetRequest(BaseModel):
    pin: str


class PinResponse(BaseModel):
    classId: str
    month: str
    pin: str | None
