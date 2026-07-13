from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from core.safari.domain import SafariMapInfluence


@dataclass(slots=True)
class SafariWorld:
    guild_id: int
    current_progress: int
    daily_unlock_count: int
    current_influence: SafariMapInfluence = field(default_factory=SafariMapInfluence)
    last_daily_reset_date: date | None = None

    @classmethod
    def create(cls, guild_id: int, reset_date: date) -> "SafariWorld":
        return cls(
            guild_id=guild_id,
            current_progress=0,
            daily_unlock_count=0,
            current_influence=SafariMapInfluence(),
            last_daily_reset_date=reset_date,
        )

    def __post_init__(self) -> None:
        if self.guild_id <= 0:
            raise ValueError("guild_id must be positive.")

        if self.current_progress < 0:
            raise ValueError("current_progress cannot be negative.")

        if self.daily_unlock_count < 0:
            raise ValueError("daily_unlock_count cannot be negative.")

        if self.last_daily_reset_date is None:
            raise ValueError("last_daily_reset_date is required.")
