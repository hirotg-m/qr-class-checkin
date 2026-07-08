from __future__ import annotations

import uuid

from app.repositories.dynamodb import get_table

TABLE = "Participants"


def _pk(class_id: str) -> str:
    return f"CLASS#{class_id}"


def _sk(participant_id: str) -> str:
    return f"PARTICIPANT#{participant_id}"


def list_by_class(class_id: str) -> list[dict]:
    table = get_table(TABLE)
    response = table.query(
        KeyConditionExpression="PK = :pk", ExpressionAttributeValues={":pk": _pk(class_id)}
    )
    return [_from_item(item) for item in response.get("Items", [])]


def get(class_id: str, participant_id: str) -> dict | None:
    table = get_table(TABLE)
    response = table.get_item(Key={"PK": _pk(class_id), "SK": _sk(participant_id)})
    item = response.get("Item")
    return _from_item(item) if item else None


def create(class_id: str, name: str, grade: str, first_seen_date: str) -> dict:
    table = get_table(TABLE)
    participant_id = uuid.uuid4().hex[:12]
    item = {
        "PK": _pk(class_id),
        "SK": _sk(participant_id),
        "participantId": participant_id,
        "name": name,
        "grade": grade,
        "firstSeenDate": first_seen_date,
    }
    table.put_item(Item=item)
    return _from_item(item)


def update(class_id: str, participant_id: str, name: str, grade: str) -> dict:
    table = get_table(TABLE)
    table.update_item(
        Key={"PK": _pk(class_id), "SK": _sk(participant_id)},
        UpdateExpression="SET #name = :name, grade = :grade",
        ExpressionAttributeNames={"#name": "name"},
        ExpressionAttributeValues={":name": name, ":grade": grade},
    )
    return get(class_id, participant_id)  # type: ignore[return-value]


def delete(class_id: str, participant_id: str) -> None:
    table = get_table(TABLE)
    table.delete_item(Key={"PK": _pk(class_id), "SK": _sk(participant_id)})


def _from_item(item: dict) -> dict:
    return {
        "participantId": item["participantId"],
        "name": item["name"],
        "grade": item["grade"],
        "firstSeenDate": item.get("firstSeenDate"),
    }
