import json
from collections.abc import Mapping

from core.safari.daily_progress import SafariDailyWorld
from core.safari.domain import SafariMapInfluence
from infrastructure.safari.world_mapper import SafariWorldMapper


class SafariDailyWorldMapper:
    @staticmethod
    def from_row(row) -> SafariDailyWorld:
        return SafariDailyWorld(
            guild_id=row["guild_id"],
            cycle_date=row["cycle_date"],
            daily_capture_count=row["daily_capture_count"],
            daily_unlock_count=row["daily_unlock_count"],
            current_influence=SafariMapInfluence(
                SafariWorldMapper._decode_influence(row["current_influence"]),
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
        validated = SafariWorldMapper._validate_influence(dict(amounts))
        return json.dumps(validated, sort_keys=True)
