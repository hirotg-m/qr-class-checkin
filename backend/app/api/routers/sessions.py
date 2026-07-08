from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.api.deps import get_current_claims, require_admin
from app.api.routers._shared import build_checkin_response
from app.core.errors import AppError
from app.domain import checkin_service
from app.repositories import classes_repo, participants_repo, schedule_repo, session_log_repo
from app.schemas.common import grade_sort_key
from app.schemas.participant_schemas import ParticipantListItem, ParticipantResponse, ParticipantUpdateRequest
from app.schemas.public_schemas import (
    CheckinConfirmResponse,
    CheckinConfirmResultItem,
    CheckinResponse,
    ProxyCheckinRequest,
    ProxyConfirmRequest,
)
from app.schemas.schedule_schemas import ScheduleResponse
from app.schemas.session_schemas import ParticipantView, SessionResponse

router = APIRouter(tags=["sessions"])


def _require_class(class_id: str) -> None:
    if classes_repo.get_class(class_id) is None:
        raise AppError("NOT_FOUND", 404, "クラスが見つかりません")


@router.get("/classes/{class_id}/sessions/{date}", response_model=SessionResponse)
def get_session(class_id: str, date: str, claims: dict = Depends(get_current_claims)) -> SessionResponse:
    _require_class(class_id)
    schedule = schedule_repo.get(class_id, date)
    logs = session_log_repo.list_by_date(class_id, date)
    participants = {p["participantId"]: p for p in participants_repo.list_by_class(class_id)}

    views = []
    for log in logs:
        participant = participants.get(log["participantId"])
        if participant is None:
            continue
        visit_dates = sorted(session_log_repo.list_dates_by_participant(class_id, participant["participantId"]))
        earlier_dates = [d for d in visit_dates if d < date]
        views.append(
            ParticipantView(
                participantId=participant["participantId"],
                name=participant["name"],
                grade=participant["grade"],
                isNew=log["isNew"],
                checkedInAt=log["checkedInAt"],
                inputBy=log["inputBy"],
                visitCount=len(earlier_dates),
                previousDate=earlier_dates[-1] if earlier_dates else None,
            )
        )

    views.sort(key=lambda p: (grade_sort_key(p.grade), p.name))

    return SessionResponse(
        date=date,
        schedule=ScheduleResponse(**schedule) if schedule else None,
        participants=views,
    )


@router.post("/classes/{class_id}/sessions/{date}/proxy", response_model=CheckinResponse)
def proxy_checkin(
    class_id: str, date: str, payload: ProxyCheckinRequest, claims: dict = Depends(get_current_claims)
) -> CheckinResponse:
    children = [checkin_service.ChildInput(name=c.name, grade=c.grade) for c in payload.children]
    results = checkin_service.evaluate_batch(
        class_id, children, date=date, enforce_reception_window=claims.get("role") != "admin"
    )
    return build_checkin_response(results)


@router.post(
    "/classes/{class_id}/sessions/{date}/proxy/confirm",
    response_model=CheckinConfirmResponse,
    status_code=201,
)
def proxy_confirm(
    class_id: str, date: str, payload: ProxyConfirmRequest, claims: dict = Depends(get_current_claims)
) -> CheckinConfirmResponse:
    confirmations = [
        checkin_service.Confirmation(
            index=c.index, action=c.action, participant_id=c.participantId, name=c.name, grade=c.grade
        )
        for c in payload.confirmations
    ]
    results = checkin_service.confirm_batch(
        class_id,
        confirmations,
        input_by="proxy",
        date=date,
        enforce_reception_window=claims.get("role") != "admin",
    )
    return CheckinConfirmResponse(
        results=[
            CheckinConfirmResultItem(
                index=r.index, participantId=r.participant_id, isNew=r.is_new, checkedInAt=r.checked_in_at
            )
            for r in results
        ]
    )


@router.delete("/classes/{class_id}/sessions/{date}/participants/{participant_id}", status_code=204)
def delete_session_participant(
    class_id: str, date: str, participant_id: str, claims: dict = Depends(require_admin)
) -> Response:
    """管理者による来場記録の取り消し（誤って登録した参加者の削除）。参加者名簿自体は削除しない。"""
    _require_class(class_id)
    session_log_repo.delete(class_id, date, participant_id)
    return Response(status_code=204)


@router.get("/classes/{class_id}/participants", response_model=list[ParticipantListItem])
def list_participants(class_id: str, claims: dict = Depends(get_current_claims)) -> list[ParticipantListItem]:
    """参加者名簿。viewer/adminどちらも閲覧可（編集はadminのみ、5.5節）。"""
    _require_class(class_id)
    items = []
    for participant in participants_repo.list_by_class(class_id):
        visit_count = len(session_log_repo.list_dates_by_participant(class_id, participant["participantId"]))
        items.append(
            ParticipantListItem(
                participantId=participant["participantId"],
                name=participant["name"],
                grade=participant["grade"],
                firstSeenDate=participant["firstSeenDate"],
                visitCount=visit_count,
            )
        )
    items.sort(key=lambda p: (grade_sort_key(p.grade), p.name))
    return items


@router.put("/classes/{class_id}/participants/{participant_id}", response_model=ParticipantResponse)
def update_participant(
    class_id: str, participant_id: str, payload: ParticipantUpdateRequest, claims: dict = Depends(require_admin)
) -> ParticipantResponse:
    """管理者による参加者情報の修正（表記ゆれ・入力ミスの訂正）。"""
    class_obj = classes_repo.get_class(class_id)
    if class_obj is None:
        raise AppError("NOT_FOUND", 404, "クラスが見つかりません")
    if participants_repo.get(class_id, participant_id) is None:
        raise AppError("NOT_FOUND", 404, "参加者が見つかりません")
    if payload.grade not in class_obj["targetGrades"]:
        raise AppError("GRADE_NOT_ALLOWED", 400, f"学年「{payload.grade}」はこのクラスの対象学年ではありません")
    updated = participants_repo.update(class_id, participant_id, payload.name, payload.grade)
    return ParticipantResponse(**updated)


@router.delete("/classes/{class_id}/participants/{participant_id}", status_code=204)
def delete_participant(class_id: str, participant_id: str, claims: dict = Depends(require_admin)) -> Response:
    """参加者名簿からの削除。過去の`SessionLog`は残るが、参加者名が引けなくなるため一覧・統計には
    表示されなくなる（`REQUIREMENTS.md` 6節：関連レコードの扱いは未決のため、この挙動を採用）。"""
    _require_class(class_id)
    participants_repo.delete(class_id, participant_id)
    return Response(status_code=204)
