from __future__ import annotations

from pydantic import BaseModel, field_validator

from app.schemas.common import validate_grade


class ParticipantUpdateRequest(BaseModel):
    name: str
    grade: str

    @field_validator("grade")
    @classmethod
    def _validate_grade(cls, value: str) -> str:
        return validate_grade(value)


class ParticipantResponse(BaseModel):
    participantId: str
    name: str
    grade: str
    firstSeenDate: str | None


class ParticipantListItem(BaseModel):
    participantId: str
    name: str
    grade: str
    firstSeenDate: str | None
    visitCount: int
