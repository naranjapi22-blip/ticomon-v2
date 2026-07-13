from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from core.safari.domain import SafariMapInfluence, SafariUnlockStatus


class SafariUnlockAlreadyConsumed(ValueError):
    pass


@dataclass(slots=True)
class SafariUnlock:
    id: int | None
    guild_id: int
    level: int
    encounter_count: int
    balls_per_participant: int
    unlocked_at: datetime
    map_influence: SafariMapInfluence = field(default_factory=SafariMapInfluence)
    status: SafariUnlockStatus = SafariUnlockStatus.AVAILABLE
    consumed_at: datetime | None = None
    consumed_session_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.guild_id <= 0:
            raise ValueError("guild_id must be positive.")

        if self.level <= 0:
            raise ValueError("level must be positive.")

        if self.encounter_count <= 0:
            raise ValueError("encounter_count must be positive.")

        if self.balls_per_participant <= 0:
            raise ValueError("balls_per_participant must be positive.")

        if self.unlocked_at is None:
            raise ValueError("unlocked_at is required.")

        if self.status == SafariUnlockStatus.AVAILABLE:
            if self.consumed_at is not None or self.consumed_session_id is not None:
                raise ValueError(
                    "available unlocks cannot have consumption data.",
                )

        if self.status == SafariUnlockStatus.CONSUMED:
            if self.consumed_at is None or self.consumed_session_id is None:
                raise ValueError(
                    "consumed unlocks require consumption data.",
                )

    def consume(
        self,
        consumed_at: datetime,
        session_id: UUID,
    ) -> None:
        if consumed_at is None or session_id is None:
            raise ValueError("consumed_at and session_id are required.")

        if self.status != SafariUnlockStatus.AVAILABLE:
            raise SafariUnlockAlreadyConsumed("Unlock is already consumed.")

        self.status = SafariUnlockStatus.CONSUMED
        self.consumed_at = consumed_at
        self.consumed_session_id = session_id
