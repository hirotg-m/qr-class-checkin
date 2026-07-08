from __future__ import annotations

from app.repositories.dynamodb import get_table

TABLE = "Classes"


def _pk(class_id: str) -> str:
    return f"CLASS#{class_id}"


def list_classes() -> list[dict]:
    table = get_table(TABLE)
    response = table.scan()
    return [_from_item(item) for item in response.get("Items", [])]


def get_class(class_id: str) -> dict | None:
    table = get_table(TABLE)
    response = table.get_item(Key={"PK": _pk(class_id)})
    item = response.get("Item")
    return _from_item(item) if item else None


def create_class(class_id: str, name: str, description: str, target_grades: list[str]) -> dict:
    table = get_table(TABLE)
    item = {
        "PK": _pk(class_id),
        "classId": class_id,
        "name": name,
        "description": description,
        "targetGrades": target_grades,
    }
    table.put_item(Item=item)
    return _from_item(item)


def update_class(class_id: str, name: str, description: str, target_grades: list[str]) -> dict:
    return create_class(class_id, name, description, target_grades)


def delete_class(class_id: str) -> None:
    table = get_table(TABLE)
    table.delete_item(Key={"PK": _pk(class_id)})


def _from_item(item: dict) -> dict:
    return {
        "classId": item["classId"],
        "name": item["name"],
        "description": item.get("description", ""),
        "targetGrades": list(item.get("targetGrades", [])),
    }
