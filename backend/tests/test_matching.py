from __future__ import annotations

from app.domain.matching import MatchStatus, Participant, match_participant

ROSTER = [
    Participant("p1", "山田太郎", "小5"),
    Participant("p2", "鈴木花子", "小2"),
]


def test_exact_match_returns_confirmed():
    result = match_participant(ROSTER, "山田太郎", "小5")
    assert result.status == MatchStatus.CONFIRMED
    assert result.participant.participant_id == "p1"


def test_similar_name_returns_candidates():
    result = match_participant(ROSTER, "山田太朗", "小5")
    assert result.status == MatchStatus.CANDIDATES
    assert result.candidates[0].participant_id == "p1"


def test_different_grade_does_not_match_same_name():
    result = match_participant(ROSTER, "山田太郎", "小6")
    assert result.status == MatchStatus.NEW


def test_completely_different_name_returns_new():
    result = match_participant(ROSTER, "佐藤次郎", "小5")
    assert result.status == MatchStatus.NEW
    assert result.proposed_name == "佐藤次郎"
    assert result.proposed_grade == "小5"


def test_empty_roster_returns_new():
    result = match_participant([], "山田太郎", "小5")
    assert result.status == MatchStatus.NEW
