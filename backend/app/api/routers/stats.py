from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_claims
from app.core.errors import AppError
from app.repositories import classes_repo, participants_repo, schedule_repo, session_log_repo
from app.schemas.stats_schemas import StatsEntry

router = APIRouter(tags=["stats"])


@router.get("/classes/{class_id}/stats/participants", response_model=list[StatsEntry])
def get_stats(
    class_id: str,
    from_: str = Query(alias="from"),
    to: str = Query(...),
    claims: dict = Depends(get_current_claims),
) -> list[StatsEntry]:
    if classes_repo.get_class(class_id) is None:
        raise AppError("NOT_FOUND", 404, "クラスが見つかりません")

    participants_by_id = {p["participantId"]: p for p in participants_repo.list_by_class(class_id)}
    schedule_entries = schedule_repo.list_by_range(class_id, from_, to)

    results: list[StatsEntry] = []
    for entry in schedule_entries:
        logs = session_log_repo.list_by_date(class_id, entry["date"])
        by_grade: dict[str, int] = {}
        for log in logs:
            participant = participants_by_id.get(log["participantId"])
            if participant is None:
                continue
            grade = participant["grade"]
            by_grade[grade] = by_grade.get(grade, 0) + 1
        results.append(StatsEntry(date=entry["date"], total=len(logs), byGrade=by_grade))
    return results
