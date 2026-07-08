from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.errors import AppError
from app.domain import matching
from app.domain.reception_window import ScheduleEntry, is_accepting_now
from app.repositories import classes_repo, participants_repo, schedule_repo, session_log_repo

JST = timezone(timedelta(hours=9))


@dataclass
class ChildInput:
    name: str
    grade: str


@dataclass
class EvaluateResult:
    index: int
    status: str
    participant: dict | None = None
    candidates: list[dict] | None = None
    proposed_name: str | None = None
    proposed_grade: str | None = None


@dataclass
class Confirmation:
    index: int
    action: str
    participant_id: str | None = None
    name: str | None = None
    grade: str | None = None


@dataclass
class ConfirmResult:
    index: int
    participant_id: str
    is_new: bool
    checked_in_at: str


def _require_class(class_id: str) -> dict:
    class_obj = classes_repo.get_class(class_id)
    if class_obj is None:
        raise AppError("NOT_FOUND", 404, "クラスが見つかりません")
    return class_obj


def _resolve_date(date: str | None, now: datetime) -> str:
    return date or now.strftime("%Y-%m-%d")


def _require_accepting(class_id: str, date: str, now: datetime) -> None:
    schedule = schedule_repo.get(class_id, date)
    entry = (
        ScheduleEntry(date=schedule["date"], start_time=schedule["startTime"], end_time=schedule["endTime"])
        if schedule
        else None
    )
    if not is_accepting_now(entry, now):
        raise AppError("OUTSIDE_RECEPTION_HOURS", 403, "現在は受付時間外です")


def _check_grades_allowed(class_obj: dict, children: list[ChildInput]) -> None:
    allowed = set(class_obj["targetGrades"])
    for index, child in enumerate(children):
        if child.grade not in allowed:
            raise AppError(
                "GRADE_NOT_ALLOWED",
                400,
                f"学年「{child.grade}」はこのクラスの対象学年ではありません",
                index=index,
            )


def evaluate_batch(
    class_id: str,
    children: list[ChildInput],
    date: str | None = None,
    now: datetime | None = None,
    enforce_reception_window: bool = True,
) -> list[EvaluateResult]:
    """docs/api.md 1.3節・5.2節。PIN/認証の検証は呼び出し側（router）が行う。
    enforce_reception_window=False は管理者による過去日の代理入力修正用（5.2節）。"""
    now = now or datetime.now(JST)
    resolved_date = _resolve_date(date, now)
    class_obj = _require_class(class_id)
    if enforce_reception_window:
        _require_accepting(class_id, resolved_date, now)
    _check_grades_allowed(class_obj, children)

    roster = [
        matching.Participant(p["participantId"], p["name"], p["grade"])
        for p in participants_repo.list_by_class(class_id)
    ]

    results: list[EvaluateResult] = []
    for index, child in enumerate(children):
        match = matching.match_participant(roster, child.name, child.grade)
        if match.status == matching.MatchStatus.CONFIRMED:
            results.append(
                EvaluateResult(
                    index=index,
                    status="confirmed",
                    participant={
                        "participantId": match.participant.participant_id,
                        "name": match.participant.name,
                        "grade": match.participant.grade,
                    },
                )
            )
        elif match.status == matching.MatchStatus.CANDIDATES:
            results.append(
                EvaluateResult(
                    index=index,
                    status="candidates",
                    candidates=[
                        {"participantId": c.participant_id, "name": c.name, "grade": c.grade}
                        for c in match.candidates
                    ],
                )
            )
        else:
            results.append(
                EvaluateResult(
                    index=index, status="new", proposed_name=match.proposed_name, proposed_grade=match.proposed_grade
                )
            )
    return results


def confirm_batch(
    class_id: str,
    confirmations: list[Confirmation],
    input_by: str,
    date: str | None = None,
    now: datetime | None = None,
    enforce_reception_window: bool = True,
) -> list[ConfirmResult]:
    """docs/api.md 1.4節・5.3節。enforce_reception_window=False は管理者による過去日の代理入力修正用。"""
    now = now or datetime.now(JST)
    resolved_date = _resolve_date(date, now)
    class_obj = _require_class(class_id)
    if enforce_reception_window:
        _require_accepting(class_id, resolved_date, now)

    results: list[ConfirmResult] = []
    for confirmation in confirmations:
        if confirmation.action == "create_new":
            if confirmation.grade not in class_obj["targetGrades"]:
                raise AppError(
                    "GRADE_NOT_ALLOWED",
                    400,
                    f"学年「{confirmation.grade}」はこのクラスの対象学年ではありません",
                    index=confirmation.index,
                )
            participant = participants_repo.create(
                class_id, confirmation.name, confirmation.grade, resolved_date
            )
            participant_id = participant["participantId"]
            is_new = True
        else:
            existing = participants_repo.get(class_id, confirmation.participant_id)
            if existing is None:
                raise AppError("NOT_FOUND", 404, "参加者が見つかりません", index=confirmation.index)
            participant_id = existing["participantId"]
            is_new = False

        checked_in_at = now.isoformat()
        try:
            session_log_repo.record_checkin(
                class_id, resolved_date, participant_id, is_new, checked_in_at, input_by
            )
        except AppError as exc:
            exc.index = confirmation.index
            raise
        results.append(
            ConfirmResult(
                index=confirmation.index,
                participant_id=participant_id,
                is_new=is_new,
                checked_in_at=checked_in_at,
            )
        )
    return results
