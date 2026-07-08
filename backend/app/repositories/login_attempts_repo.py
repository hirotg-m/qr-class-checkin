from __future__ import annotations

import time

from app.repositories.dynamodb import get_table

TABLE = "LoginAttempts"
WINDOW_SECONDS = 3 * 60
MAX_ATTEMPTS = 10


def _pk(ip: str) -> str:
    return f"IP#{ip}"


def _get_active(ip: str) -> dict | None:
    table = get_table(TABLE)
    response = table.get_item(Key={"PK": _pk(ip)})
    item = response.get("Item")
    if item and int(item.get("expiresAt", 0)) > int(time.time()):
        return item
    return None


def is_locked(ip: str) -> bool:
    item = _get_active(ip)
    return item is not None and int(item.get("failCount", 0)) >= MAX_ATTEMPTS


def record_failure(ip: str) -> None:
    table = get_table(TABLE)
    item = _get_active(ip)
    fail_count = int(item["failCount"]) + 1 if item else 1
    table.put_item(
        Item={
            "PK": _pk(ip),
            "failCount": fail_count,
            "expiresAt": int(time.time()) + WINDOW_SECONDS,
        }
    )


def reset(ip: str) -> None:
    table = get_table(TABLE)
    table.delete_item(Key={"PK": _pk(ip)})
