from __future__ import annotations

from pydantic import BaseModel


class StatsEntry(BaseModel):
    date: str
    total: int
    byGrade: dict[str, int]
