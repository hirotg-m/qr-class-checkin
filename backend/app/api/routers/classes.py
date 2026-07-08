from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response

from app.api.deps import get_current_claims, require_admin
from app.core.errors import AppError
from app.repositories import classes_repo
from app.schemas.class_schemas import ClassCreateRequest, ClassResponse, ClassUpdateRequest

router = APIRouter(tags=["classes"])


@router.get("/classes", response_model=list[ClassResponse])
def list_classes(claims: dict = Depends(get_current_claims)) -> list[ClassResponse]:
    return [ClassResponse(**c) for c in classes_repo.list_classes()]


@router.post("/classes", response_model=ClassResponse, status_code=201)
def create_class(payload: ClassCreateRequest, claims: dict = Depends(require_admin)) -> ClassResponse:
    class_id = uuid.uuid4().hex[:10]
    created = classes_repo.create_class(class_id, payload.name, payload.description, payload.targetGrades)
    return ClassResponse(**created)


@router.put("/classes/{class_id}", response_model=ClassResponse)
def update_class(
    class_id: str, payload: ClassUpdateRequest, claims: dict = Depends(require_admin)
) -> ClassResponse:
    if classes_repo.get_class(class_id) is None:
        raise AppError("NOT_FOUND", 404, "クラスが見つかりません")
    updated = classes_repo.update_class(class_id, payload.name, payload.description, payload.targetGrades)
    return ClassResponse(**updated)


@router.delete("/classes/{class_id}", status_code=204)
def delete_class(class_id: str, claims: dict = Depends(require_admin)) -> Response:
    if classes_repo.get_class(class_id) is None:
        raise AppError("NOT_FOUND", 404, "クラスが見つかりません")
    classes_repo.delete_class(class_id)
    return Response(status_code=204)
