from __future__ import annotations

import time
from typing import Literal

import jwt

from app.core import config
from app.core.errors import AppError

Role = Literal["viewer", "admin"]

_ALGORITHM = "HS256"


def create_auth_token(role: Role) -> tuple[str, int]:
    """指導者・管理者ログイン用トークン（REQUIREMENTS.md 8.2節）。"""
    ttl = config.AUTH_TOKEN_TTL_SECONDS
    payload = {"role": role, "exp": int(time.time()) + ttl}
    token = jwt.encode(payload, config.jwt_secret(), algorithm=_ALGORITHM)
    return token, ttl


def verify_auth_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, config.jwt_secret(), algorithms=[_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise AppError("UNAUTHORIZED", 401, "認証トークンが無効です") from exc
    if payload.get("type") == "checkin" or payload.get("role") not in ("viewer", "admin"):
        raise AppError("UNAUTHORIZED", 401, "認証トークンが無効です")
    return payload


def create_checkin_token(class_id: str) -> tuple[str, int]:
    """保護者向けPIN検証後に発行する短命トークン（docs/api.md 1.2節）。"""
    ttl = config.CHECKIN_TOKEN_TTL_SECONDS
    payload = {"type": "checkin", "classId": class_id, "exp": int(time.time()) + ttl}
    token = jwt.encode(payload, config.jwt_secret(), algorithm=_ALGORITHM)
    return token, ttl


def verify_checkin_token(token: str, class_id: str) -> dict:
    try:
        payload = jwt.decode(token, config.jwt_secret(), algorithms=[_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise AppError("UNAUTHORIZED", 401, "チェックイン用トークンが無効です") from exc
    if payload.get("type") != "checkin" or payload.get("classId") != class_id:
        raise AppError("UNAUTHORIZED", 401, "チェックイン用トークンが無効です")
    return payload


def resolve_login_role(code: str) -> Role | None:
    if code == config.teacher_code():
        return "viewer"
    if code == config.admin_code():
        return "admin"
    return None
