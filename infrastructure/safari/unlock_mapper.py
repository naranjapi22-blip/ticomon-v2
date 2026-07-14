import json
from collections.abc import Mapping
from datetime import UTC, datetime

from core.safari.domain import SafariMapInfluence, SafariUnlockStatus
from core.safari.unlock import SafariUnlock


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
                SafariUnlockMapper._decode_influence(row["map_influence"]),
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
            SafariUnlockMapper.encode_influence(unlock.map_influence.amounts),
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

    @staticmethod
    def encode_influence(amounts: Mapping[str, int]) -> str:
        validated = SafariUnlockMapper._validate_influence(dict(amounts))
        return json.dumps(validated, sort_keys=True)

    @staticmethod
    def _decode_influence(value) -> dict[str, int]:
        decoded = json.loads(value) if isinstance(value, str) else dict(value)
        return SafariUnlockMapper._validate_influence(decoded)

    @staticmethod
    def _validate_influence(value: Mapping) -> dict[str, int]:
        validated: dict[str, int] = {}

        for type_name, amount in value.items():
            if (
                not isinstance(type_name, str)
                or not type_name
                or type_name != type_name.strip().lower()
            ):
                raise ValueError("Influence type names must be canonical lowercase.")

            if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
                raise ValueError("Influence amounts must be non-negative integers.")

            validated[type_name] = amount

        return validated
