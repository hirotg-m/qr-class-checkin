from __future__ import annotations

from fastapi import APIRouter, Request

from app.core import security
from app.core.errors import AppError
from app.repositories import login_attempts_repo
from app.schemas.auth_schemas import LoginRequest, LoginResponse

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request) -> LoginResponse:
    client_ip = request.client.host if request.client else "unknown"

    if login_attempts_repo.is_locked(client_ip):
        raise AppError("RATE_LIMITED", 429, "ログイン試行回数が上限を超えました。しばらく待ってから再試行してください")

    role = security.resolve_login_role(payload.code)
    if role is None:
        login_attempts_repo.record_failure(client_ip)
        raise AppError("UNAUTHORIZED", 401, "コードが正しくありません")

    login_attempts_repo.reset(client_ip)
    token, expires_in = security.create_auth_token(role)
    return LoginResponse(token=token, role=role, expiresIn=expires_in)
