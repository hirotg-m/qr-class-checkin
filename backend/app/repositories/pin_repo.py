from __future__ import annotations

from app.repositories.dynamodb import get_table

TABLE = "MonthlyPin"


def _pk(class_id: str, month: str) -> str:
    return f"CLASS#{class_id}#MONTH#{month}"


def get_pin(class_id: str, month: str) -> str | None:
    table = get_table(TABLE)
    response = table.get_item(Key={"PK": _pk(class_id, month)})
    item = response.get("Item")
    return item["pin"] if item else None


def set_pin(class_id: str, month: str, pin: str) -> None:
    table = get_table(TABLE)
    table.put_item(Item={"PK": _pk(class_id, month), "pin": pin})
