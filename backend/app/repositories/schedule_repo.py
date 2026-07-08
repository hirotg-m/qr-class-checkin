from __future__ import annotations

from app.core.errors import AppError
from app.repositories.dynamodb import get_table

TABLE = "Schedule"


def _pk(class_id: str) -> str:
    return f"CLASS#{class_id}"


def _sk(date: str) -> str:
    return f"DATE#{date}"


def list_by_month(class_id: str, month: str) -> list[dict]:
    """month: yyyy-mm"""
    table = get_table(TABLE)
    response = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={":pk": _pk(class_id), ":sk_prefix": f"DATE#{month}"},
    )
    return [_from_item(item) for item in response.get("Items", [])]


def list_by_range(class_id: str, date_from: str, date_to: str) -> list[dict]:
    table = get_table(TABLE)
    response = table.query(
        KeyConditionExpression="PK = :pk AND SK BETWEEN :from_sk AND :to_sk",
        ExpressionAttributeValues={
            ":pk": _pk(class_id),
            ":from_sk": _sk(date_from),
            ":to_sk": _sk(date_to),
        },
    )
    return [_from_item(item) for item in response.get("Items", [])]


def get(class_id: str, date: str) -> dict | None:
    table = get_table(TABLE)
    response = table.get_item(Key={"PK": _pk(class_id), "SK": _sk(date)})
    item = response.get("Item")
    return _from_item(item) if item else None


def create(class_id: str, date: str, start_time: str, end_time: str, location: str) -> dict:
    table = get_table(TABLE)
    item = {
        "PK": _pk(class_id),
        "SK": _sk(date),
        "date": date,
        "startTime": start_time,
        "endTime": end_time,
        "location": location,
    }
    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)",
        )
    except table.meta.client.exceptions.ConditionalCheckFailedException as exc:
        raise AppError("CONFLICT", 409, "指定日の活動予定は既に登録されています") from exc
    return _from_item(item)


def update(class_id: str, date: str, start_time: str, end_time: str, location: str) -> dict:
    table = get_table(TABLE)
    item = {
        "PK": _pk(class_id),
        "SK": _sk(date),
        "date": date,
        "startTime": start_time,
        "endTime": end_time,
        "location": location,
    }
    table.put_item(Item=item)
    return _from_item(item)


def delete(class_id: str, date: str) -> None:
    table = get_table(TABLE)
    table.delete_item(Key={"PK": _pk(class_id), "SK": _sk(date)})


def _from_item(item: dict) -> dict:
    return {
        "date": item["date"],
        "startTime": item["startTime"],
        "endTime": item["endTime"],
        "location": item.get("location", ""),
    }
