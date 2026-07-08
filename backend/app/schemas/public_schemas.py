from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TodaySessionView(BaseModel):
    date: str
    startTime: str
    endTime: str
    acceptingNow: bool


class ClassInfoResponse(BaseModel):
    classId: str
    className: str
    targetGrades: list[str]
    todaySession: TodaySessionView | None


class PinVerifyRequest(BaseModel):
    pin: str


class PinVerifyResponse(BaseModel):
    checkinToken: str
    expiresIn: int


class ChildInput(BaseModel):
    name: str
    grade: str


class CheckinRequest(BaseModel):
    checkinToken: str
    children: list[ChildInput]
    inputBy: Literal["self", "proxy"] = "self"


class ProxyCheckinRequest(BaseModel):
    children: list[ChildInput]


class CandidateView(BaseModel):
    participantId: str
    name: str
    grade: str


class CheckinResultItem(BaseModel):
    index: int
    status: Literal["confirmed", "candidates", "new"]
    participantId: str | None = None
    isNew: bool | None = None
    candidates: list[CandidateView] | None = None
    proposedName: str | None = None
    proposedGrade: str | None = None


class CheckinResponse(BaseModel):
    results: list[CheckinResultItem]


class ConfirmationItem(BaseModel):
    index: int
    action: Literal["select_existing", "create_new"]
    participantId: str | None = None
    name: str | None = None
    grade: str | None = None


class CheckinConfirmRequest(BaseModel):
    checkinToken: str
    confirmations: list[ConfirmationItem] = Field(default_factory=list)
    inputBy: Literal["self", "proxy"] = "self"


class ProxyConfirmRequest(BaseModel):
    confirmations: list[ConfirmationItem] = Field(default_factory=list)


class CheckinConfirmResultItem(BaseModel):
    index: int
    participantId: str
    isNew: bool
    checkedInAt: str


class CheckinConfirmResponse(BaseModel):
    results: list[CheckinConfirmResultItem]
