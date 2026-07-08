from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.api.deps import get_current_claims, require_admin
from app.core.errors import AppError
from app.repositories import classes_repo, schedule_repo
from app.schemas.schedule_schemas import ScheduleCreateRequest, ScheduleResponse, ScheduleUpdateRequest

router = APIRouter(tags=["schedule"])


def _require_class(class_id: str) -> None:
    if classes_repo.get_class(class_id) is None:
        raise AppError("NOT_FOUND", 404, "クラスが見つかりません")


@router.get("/classes/{class_id}/schedule", response_model=list[ScheduleResponse])
def list_schedule(class_id: str, month: str, claims: dict = Depends(get_current_claims)) -> list[ScheduleResponse]:
    _require_class(class_id)
    return [ScheduleResponse(**s) for s in schedule_repo.list_by_month(class_id, month)]


@router.post("/classes/{class_id}/schedule", response_model=ScheduleResponse, status_code=201)
def create_schedule(
    class_id: str, payload: ScheduleCreateRequest, claims: dict = Depends(require_admin)
) -> ScheduleResponse:
    _require_class(class_id)
    created = schedule_repo.create(class_id, payload.date, payload.startTime, payload.endTime, payload.location)
    return ScheduleResponse(**created)


@router.put("/classes/{class_id}/schedule/{date}", response_model=ScheduleResponse)
def update_schedule(
    class_id: str, date: str, payload: ScheduleUpdateRequest, claims: dict = Depends(require_admin)
) -> ScheduleResponse:
    _require_class(class_id)
    if schedule_repo.get(class_id, date) is None:
        raise AppError("NOT_FOUND", 404, "活動予定が見つかりません")
    updated = schedule_repo.update(class_id, date, payload.startTime, payload.endTime, payload.location)
    return ScheduleResponse(**updated)


@router.delete("/classes/{class_id}/schedule/{date}", status_code=204)
def delete_schedule(class_id: str, date: str, claims: dict = Depends(require_admin)) -> Response:
    _require_class(class_id)
    schedule_repo.delete(class_id, date)
    return Response(status_code=204)
