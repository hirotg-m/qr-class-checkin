from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    code: str


class LoginResponse(BaseModel):
    token: str
    role: str
    expiresIn: int
