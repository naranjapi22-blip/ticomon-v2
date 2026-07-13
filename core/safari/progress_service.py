from __future__ import annotations

from datetime import date, datetime

from core.safari.domain import SAFARI_LEVEL_CONFIGS, SafariMapInfluence
from core.safari.progress_result import SafariWorldProgressResult
from core.safari.unlock import SafariUnlock
from core.safari.world import SafariWorld

SAFARI_UNLOCK_THRESHOLD = 100


class SafariWorldProgressService:
    def register_capture(
        self,
        world: SafariWorld,
        species_types: list[str] | tuple[str, ...],
        captured_at: date | datetime,
        progress_amount: int = 1,
    ) -> SafariWorldProgressResult:
        if progress_amount <= 0:
            raise ValueError("progress_amount must be positive.")

        normalized_types = tuple(
            dict.fromkeys(
                self._normalize_type(type_name) for type_name in species_types
            )
        )

        if not normalized_types:
            raise ValueError("species_types cannot be empty.")

        captured_date = self._normalize_date(captured_at)

        if captured_date < world.last_daily_reset_date:
            raise ValueError("captured_at cannot be before last_daily_reset_date.")

        if captured_date != world.last_daily_reset_date:
            world.daily_unlock_count = 0
            world.last_daily_reset_date = captured_date

        world.current_progress += progress_amount
        world.current_influence = self._merge_influence(
            world.current_influence,
            normalized_types,
        )

        created_unlocks: list[SafariUnlock] = []
        influence_snapshot = SafariMapInfluence(
            dict(world.current_influence.amounts),
        )

        while world.current_progress >= SAFARI_UNLOCK_THRESHOLD:
            world.current_progress -= SAFARI_UNLOCK_THRESHOLD
            world.daily_unlock_count += 1

            level = self._unlock_level(world.daily_unlock_count)
            unlock_influence = (
                influence_snapshot if not created_unlocks else SafariMapInfluence()
            )

            created_unlocks.append(
                SafariUnlock(
                    id=None,
                    guild_id=world.guild_id,
                    level=level,
                    encounter_count=SAFARI_LEVEL_CONFIGS[level].encounter_count,
                    balls_per_participant=(
                        SAFARI_LEVEL_CONFIGS[level].balls_per_participant
                    ),
                    map_influence=SafariMapInfluence(
                        dict(unlock_influence.amounts),
                    ),
                    unlocked_at=(
                        captured_at
                        if isinstance(captured_at, datetime)
                        else datetime.combine(captured_date, datetime.min.time())
                    ),
                )
            )

            world.current_influence = SafariMapInfluence()
            influence_snapshot = SafariMapInfluence()

        return SafariWorldProgressResult(
            created_unlocks=tuple(created_unlocks),
            current_progress=world.current_progress,
            daily_unlock_count=world.daily_unlock_count,
        )

    def _merge_influence(
        self,
        current: SafariMapInfluence,
        species_types: tuple[str, ...],
    ) -> SafariMapInfluence:
        amounts = dict(current.amounts)

        for type_name in species_types:
            amounts[type_name] = amounts.get(type_name, 0) + 1

        return SafariMapInfluence(amounts)

    def _normalize_type(self, type_name: str) -> str:
        normalized = type_name.strip().lower()
        if not normalized:
            raise ValueError("species_types cannot contain empty names.")
        return normalized

    def _normalize_date(
        self,
        captured_at: date | datetime,
    ) -> date:
        if isinstance(captured_at, datetime):
            return captured_at.date()
        return captured_at

    def _unlock_level(self, unlock_number: int) -> int:
        return min(unlock_number, max(SAFARI_LEVEL_CONFIGS))
