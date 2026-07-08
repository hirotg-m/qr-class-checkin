from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import validate_grade


class ClassCreateRequest(BaseModel):
    name: str
    description: str = ""
    targetGrades: list[str] = Field(default_factory=list)

    @field_validator("targetGrades")
    @classmethod
    def _validate_target_grades(cls, value: list[str]) -> list[str]:
        return [validate_grade(v) for v in value]


class ClassUpdateRequest(ClassCreateRequest):
    pass


class ClassResponse(BaseModel):
    classId: str
    name: str
    description: str
    targetGrades: list[str]
