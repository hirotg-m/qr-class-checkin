from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.api.routers import auth, classes, pin, public_checkin, schedule, sessions, stats
from app.core.config import ALLOWED_ORIGINS
from app.core.errors import register_exception_handlers

app = FastAPI(title="QR Class Checkin API")
register_exception_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public_checkin.router)
app.include_router(auth.router)
app.include_router(classes.router)
app.include_router(schedule.router)
app.include_router(pin.router)
app.include_router(sessions.router)
app.include_router(stats.router)

handler = Mangum(app)
