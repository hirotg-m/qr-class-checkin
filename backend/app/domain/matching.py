from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# 表記ゆれとして候補提示する氏名の編集距離の閾値（docs/backend-design.md 4.2節）
NAME_DISTANCE_THRESHOLD = 2


class MatchStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANDIDATES = "candidates"
    NEW = "new"


@dataclass(frozen=True)
class Participant:
    participant_id: str
    name: str
    grade: str


@dataclass(frozen=True)
class MatchResult:
    status: MatchStatus
    participant: Participant | None = None
    candidates: list[Participant] | None = None
    proposed_name: str | None = None
    proposed_grade: str | None = None


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    previous_row = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current_row = [i]
        for j, char_b in enumerate(b, start=1):
            insert_cost = current_row[j - 1] + 1
            delete_cost = previous_row[j] + 1
            replace_cost = previous_row[j - 1] + (char_a != char_b)
            current_row.append(min(insert_cost, delete_cost, replace_cost))
        previous_row = current_row
    return previous_row[-1]


def match_participant(roster: list[Participant], name: str, grade: str) -> MatchResult:
    """docs/backend-design.md 4.2節のマッチングロジック。
    学年が一致する参加者の中でのみ氏名を照合する（他クラスとは元々照合しない前提で、
    呼び出し側がroster自体をクラス単位に絞り込んでいること）。"""
    same_grade = [p for p in roster if p.grade == grade]

    exact = [p for p in same_grade if p.name == name]
    if exact:
        return MatchResult(status=MatchStatus.CONFIRMED, participant=exact[0])

    near = [p for p in same_grade if _levenshtein(p.name, name) <= NAME_DISTANCE_THRESHOLD]
    if near:
        return MatchResult(status=MatchStatus.CANDIDATES, candidates=near)

    return MatchResult(status=MatchStatus.NEW, proposed_name=name, proposed_grade=grade)
