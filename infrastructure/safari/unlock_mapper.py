from datetime import UTC, datetime

from core.safari.domain import SafariMapInfluence, SafariUnlockStatus
from core.safari.unlock import SafariUnlock
from infrastructure.safari.world_mapper import SafariWorldMapper


class SafariUnlockMapper:
    @staticmethod
    def from_row(row) -> SafariUnlock:
        unlocked_at = row["unlocked_at"]
        try:
            cycle_date = row["cycle_date"]
        except (KeyError, IndexError):
            cycle_date = unlocked_at.date()
        return SafariUnlock(
            id=row["id"],
            guild_id=row["guild_id"],
            level=row["level"],
            encounter_count=row["encounter_count"],
            balls_per_participant=row["balls_per_participant"],
            unlocked_at=unlocked_at,
            cycle_date=cycle_date,
            map_influence=SafariMapInfluence(
                SafariWorldMapper._decode_influence(row["map_influence"]),
            ),
            status=SafariUnlockStatus(row["status"]),
            consumed_at=row["consumed_at"],
            consumed_session_id=row["consumed_session_id"],
        )

    @staticmethod
    def to_row(unlock: SafariUnlock) -> tuple:
        return (
            unlock.guild_id,
            unlock.level,
            unlock.encounter_count,
            unlock.balls_per_participant,
            unlock.cycle_date or SafariUnlockMapper.as_utc(unlock.unlocked_at).date(),
            SafariWorldMapper.encode_influence(unlock.map_influence.amounts),
            unlock.status.value,
            SafariUnlockMapper.as_utc(unlock.unlocked_at),
            SafariUnlockMapper.as_utc(unlock.consumed_at),
            unlock.consumed_session_id,
        )

    @staticmethod
    def as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
