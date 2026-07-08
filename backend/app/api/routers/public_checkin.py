from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from app.api.routers._shared import build_checkin_response
from app.core import security
from app.core.errors import AppError
from app.domain import checkin_service
from app.domain.reception_window import ScheduleEntry, is_accepting_now
from app.repositories import classes_repo, pin_repo, schedule_repo
from app.schemas.public_schemas import (
    CheckinConfirmRequest,
    CheckinConfirmResponse,
    CheckinConfirmResultItem,
    CheckinRequest,
    CheckinResponse,
    ClassInfoResponse,
    PinVerifyRequest,
    PinVerifyResponse,
    TodaySessionView,
)

router = APIRouter(prefix="/public", tags=["public"])

JST = timezone(timedelta(hours=9))


def _now() -> datetime:
    return datetime.now(JST)


def _require_class(class_id: str) -> dict:
    class_obj = classes_repo.get_class(class_id)
    if class_obj is None:
        raise AppError("NOT_FOUND", 404, "クラスが見つかりません")
    return class_obj


@router.get("/classes/{class_id}", response_model=ClassInfoResponse)
def get_class_info(class_id: str) -> ClassInfoResponse:
    class_obj = _require_class(class_id)
    now = _now()
    today = now.strftime("%Y-%m-%d")
    schedule = schedule_repo.get(class_id, today)
    today_session = None
    if schedule:
        entry = ScheduleEntry(
            date=schedule["date"], start_time=schedule["startTime"], end_time=schedule["endTime"]
        )
        today_session = TodaySessionView(
            date=schedule["date"],
            startTime=schedule["startTime"],
            endTime=schedule["endTime"],
            acceptingNow=is_accepting_now(entry, now),
        )
    return ClassInfoResponse(
        classId=class_obj["classId"],
        className=class_obj["name"],
        targetGrades=class_obj["targetGrades"],
        todaySession=today_session,
    )


@router.post("/classes/{class_id}/pin", response_model=PinVerifyResponse)
def verify_pin(class_id: str, payload: PinVerifyRequest) -> PinVerifyResponse:
    _require_class(class_id)
    now = _now()
    month = now.strftime("%Y-%m")
    expected = pin_repo.get_pin(class_id, month)
    if expected is None or payload.pin != expected:
        raise AppError("INVALID_PIN", 401, "PINが正しくありません")
    token, expires_in = security.create_checkin_token(class_id)
    return PinVerifyResponse(checkinToken=token, expiresIn=expires_in)


@router.post("/classes/{class_id}/checkin", response_model=CheckinResponse)
def checkin(class_id: str, payload: CheckinRequest) -> CheckinResponse:
    security.verify_checkin_token(payload.checkinToken, class_id)
    children = [checkin_service.ChildInput(name=c.name, grade=c.grade) for c in payload.children]
    results = checkin_service.evaluate_batch(class_id, children)
    return build_checkin_response(results)


@router.post("/classes/{class_id}/checkin/confirm", response_model=CheckinConfirmResponse, status_code=201)
def checkin_confirm(class_id: str, payload: CheckinConfirmRequest) -> CheckinConfirmResponse:
    security.verify_checkin_token(payload.checkinToken, class_id)
    confirmations = [
        checkin_service.Confirmation(
            index=c.index,
            action=c.action,
            participant_id=c.participantId,
            name=c.name,
            grade=c.grade,
        )
        for c in payload.confirmations
    ]
    results = checkin_service.confirm_batch(class_id, confirmations, payload.inputBy)
    return CheckinConfirmResponse(
        results=[
            CheckinConfirmResultItem(
                index=r.index, participantId=r.participant_id, isNew=r.is_new, checkedInAt=r.checked_in_at
            )
            for r in results
        ]
    )
