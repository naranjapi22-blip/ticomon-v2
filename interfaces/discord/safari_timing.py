from __future__ import annotations

from datetime import UTC, datetime, timedelta

SAFARI_SELECTION_SECONDS = 45
SAFARI_ROUTE_VOTE_SECONDS = 30
SAFARI_VIEW_FALLBACK_SECONDS = 300
SAFARI_PHASE_ENDED_MESSAGE = "This phase has already ended."
SAFARI_VIEW_EXPIRED_MESSAGE = (
    "This Safari interface expired. Use !safariresume to continue."
)


def deadline_after(seconds: int) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=seconds)


def remaining_seconds(deadline: datetime | None) -> float:
    if deadline is None:
        return 0.0

    return max(0.0, (deadline - datetime.now(UTC)).total_seconds())
