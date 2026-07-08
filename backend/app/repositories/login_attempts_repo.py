from __future__ import annotations

import time

from app.repositories.dynamodb import get_table

TABLE = "LoginAttempts"
WINDOW_SECONDS = 3 * 60
MAX_ATTEMPTS = 10


def _pk(key: str) -> str:
    """key は用途ごとに名前空間を分けた任意の識別子（例: 指導者ログインは client_ip そのもの、
    保護者PIN試行は f"pin:{class_id}:{client_ip}"）。同じテーブル・同じ失敗回数/TTLロジックを
    複数の総当たり対策で共有する。"""
    return f"ATTEMPT#{key}"


def _get_active(key: str) -> dict | None:
    table = get_table(TABLE)
    response = table.get_item(Key={"PK": _pk(key)})
    item = response.get("Item")
    if item and int(item.get("expiresAt", 0)) > int(time.time()):
        return item
    return None


def is_locked(key: str) -> bool:
    item = _get_active(key)
    return item is not None and int(item.get("failCount", 0)) >= MAX_ATTEMPTS


def record_failure(key: str) -> None:
    table = get_table(TABLE)
    item = _get_active(key)
    fail_count = int(item["failCount"]) + 1 if item else 1
    table.put_item(
        Item={
            "PK": _pk(key),
            "failCount": fail_count,
            "expiresAt": int(time.time()) + WINDOW_SECONDS,
        }
    )


def reset(key: str) -> None:
    table = get_table(TABLE)
    table.delete_item(Key={"PK": _pk(key)})
