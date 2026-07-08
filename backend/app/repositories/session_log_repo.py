from __future__ import annotations

from app.core.errors import AppError
from app.repositories.dynamodb import get_table

TABLE = "SessionLog"


def _pk(class_id: str, date: str) -> str:
    return f"CLASS#{class_id}#DATE#{date}"


def _sk(participant_id: str) -> str:
    return f"PARTICIPANT#{participant_id}"


def list_by_date(class_id: str, date: str) -> list[dict]:
    table = get_table(TABLE)
    response = table.query(
        KeyConditionExpression="PK = :pk", ExpressionAttributeValues={":pk": _pk(class_id, date)}
    )
    return [_from_item(item) for item in response.get("Items", [])]


def record_checkin(
    class_id: str,
    date: str,
    participant_id: str,
    is_new: bool,
    checked_in_at: str,
    input_by: str,
) -> dict:
    table = get_table(TABLE)
    item = {
        "PK": _pk(class_id, date),
        "SK": _sk(participant_id),
        "participantId": participant_id,
        "isNew": is_new,
        "checkedInAt": checked_in_at,
        "inputBy": input_by,
    }
    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)",
        )
    except table.meta.client.exceptions.ConditionalCheckFailedException as exc:
        raise AppError("CONFLICT", 409, "既に来場記録済みです") from exc
    return _from_item(item)


def delete(class_id: str, date: str, participant_id: str) -> None:
    table = get_table(TABLE)
    table.delete_item(Key={"PK": _pk(class_id, date), "SK": _sk(participant_id)})


def list_dates_by_participant(class_id: str, participant_id: str) -> list[str]:
    """参加者の全来場日を取得する（学年別推移グラフ等と異なり日付でパーティション分割されている
    ため、単一参加者の履歴はScanで集める。クラス規模が小さい前提でのみ許容できる実装）。"""
    table = get_table(TABLE)
    response = table.scan(
        FilterExpression="begins_with(PK, :pk_prefix) AND SK = :sk",
        ExpressionAttributeValues={
            ":pk_prefix": f"CLASS#{class_id}#DATE#",
            ":sk": _sk(participant_id),
        },
    )
    return [item["PK"].rsplit("#DATE#", 1)[1] for item in response.get("Items", [])]


def _from_item(item: dict) -> dict:
    return {
        "participantId": item["participantId"],
        "isNew": item["isNew"],
        "checkedInAt": item["checkedInAt"],
        "inputBy": item["inputBy"],
    }
