import json
from collections.abc import Mapping

from core.safari.domain import SafariMapInfluence
from core.safari.world import SafariWorld


class SafariWorldMapper:
    @staticmethod
    def from_row(row) -> SafariWorld:
        return SafariWorld(
            guild_id=row["guild_id"],
            current_progress=row["current_progress"],
            daily_unlock_count=row["daily_unlock_count"],
            current_influence=SafariMapInfluence(
                SafariWorldMapper._decode_influence(row["current_influence"]),
            ),
            last_daily_reset_date=row["last_daily_reset_date"],
        )

    @staticmethod
    def to_row(world: SafariWorld) -> tuple:
        return (
            world.guild_id,
            world.current_progress,
            world.daily_unlock_count,
            SafariWorldMapper.encode_influence(world.current_influence.amounts),
            world.last_daily_reset_date,
        )

    @staticmethod
    def encode_influence(amounts: Mapping[str, int]) -> str:
        validated = SafariWorldMapper._validate_influence(dict(amounts))
        return json.dumps(validated, sort_keys=True)

    @staticmethod
    def _decode_influence(value) -> dict[str, int]:
        decoded = json.loads(value) if isinstance(value, str) else dict(value)
        return SafariWorldMapper._validate_influence(decoded)

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
