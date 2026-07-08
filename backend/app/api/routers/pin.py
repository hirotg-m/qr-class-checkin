from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_claims, require_admin
from app.core.errors import AppError
from app.repositories import classes_repo, pin_repo
from app.schemas.schedule_schemas import PinResponse, PinSetRequest

router = APIRouter(tags=["pin"])


@router.get("/classes/{class_id}/pin/{month}", response_model=PinResponse)
def get_pin(class_id: str, month: str, claims: dict = Depends(get_current_claims)) -> PinResponse:
    """QRコード掲示物へのPIN記載など、指導者・管理者向けの確認用途。保護者向け照合には使わない。"""
    if classes_repo.get_class(class_id) is None:
        raise AppError("NOT_FOUND", 404, "クラスが見つかりません")
    return PinResponse(classId=class_id, month=month, pin=pin_repo.get_pin(class_id, month))


@router.put("/classes/{class_id}/pin/{month}")
def set_pin(class_id: str, month: str, payload: PinSetRequest, claims: dict = Depends(require_admin)) -> dict:
    if classes_repo.get_class(class_id) is None:
        raise AppError("NOT_FOUND", 404, "クラスが見つかりません")
    pin_repo.set_pin(class_id, month, payload.pin)
    return {"classId": class_id, "month": month}
