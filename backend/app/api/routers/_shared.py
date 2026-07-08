from __future__ import annotations

from app.domain.checkin_service import EvaluateResult
from app.schemas.public_schemas import CandidateView, CheckinResponse, CheckinResultItem


def build_checkin_response(results: list[EvaluateResult]) -> CheckinResponse:
    """docs/api.md 1.3節・5.2節共通のレスポンス組み立て。"""
    items = []
    for r in results:
        items.append(
            CheckinResultItem(
                index=r.index,
                status=r.status,
                participantId=r.participant["participantId"] if r.participant else None,
                isNew=False if r.participant else None,
                candidates=[CandidateView(**c) for c in r.candidates] if r.candidates else None,
                proposedName=r.proposed_name,
                proposedGrade=r.proposed_grade,
            )
        )
    return CheckinResponse(results=items)
