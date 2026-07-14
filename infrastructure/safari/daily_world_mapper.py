import json
from collections.abc import Mapping

from core.safari.daily_progress import SafariDailyWorld
from core.safari.domain import SafariMapInfluence


class SafariDailyWorldMapper:
    @staticmethod
    def from_row(row) -> SafariDailyWorld:
        return SafariDailyWorld(
            guild_id=row["guild_id"],
            cycle_date=row["cycle_date"],
            daily_capture_count=row["daily_capture_count"],
            daily_unlock_count=row["daily_unlock_count"],
            current_influence=SafariMapInfluence(
                SafariDailyWorldMapper._decode_influence(row["current_influence"]),
            ),
        )

    @staticmethod
    def to_row(world: SafariDailyWorld) -> tuple:
        return (
            world.guild_id,
            world.cycle_date,
            world.daily_capture_count,
            world.daily_unlock_count,
            SafariDailyWorldMapper.encode_influence(world.current_influence.amounts),
        )

    @staticmethod
    def encode_influence(amounts: Mapping[str, int]) -> str:
        validated = SafariDailyWorldMapper._validate_influence(dict(amounts))
        return json.dumps(validated, sort_keys=True)

    @staticmethod
    def _decode_influence(value) -> dict[str, int]:
        decoded = json.loads(value) if isinstance(value, str) else dict(value)
        return SafariDailyWorldMapper._validate_influence(decoded)

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
