from __future__ import annotations

GRADES: tuple[str, ...] = (
    "小1",
    "小2",
    "小3",
    "小4",
    "小5",
    "小6",
    "中1",
    "中2",
    "中3",
)


def validate_grade(value: str) -> str:
    if value not in GRADES:
        raise ValueError(f"学年は{GRADES}のいずれかである必要があります")
    return value


def grade_sort_key(grade: str) -> int:
    """学年順（小1が先頭、中3が末尾）でのソート用キー。未知の学年は末尾に回す。"""
    return GRADES.index(grade) if grade in GRADES else len(GRADES)
