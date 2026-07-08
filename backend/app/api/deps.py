from __future__ import annotations

from fastapi import Depends, Header

from app.core import security
from app.core.errors import AppError


def get_current_claims(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "):
        raise AppError("UNAUTHORIZED", 401, "認証トークンがありません")
    token = authorization[len("Bearer ") :].strip()
    return security.verify_auth_token(token)


def require_admin(claims: dict = Depends(get_current_claims)) -> dict:
    if claims.get("role") != "admin":
        raise AppError("FORBIDDEN", 403, "管理者権限が必要です")
    return claims
