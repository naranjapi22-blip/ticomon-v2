from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from math import ceil

from core.safari.domain import SAFARI_LEVEL_CONFIGS, SafariMapInfluence
from core.safari.unlock import SafariUnlock

_SAFARI_DAILY_LEVEL_PERCENTAGES = (0.10, 0.25, 0.45, 0.70, 1.00)
_SAFARI_DAILY_MAX_UNLOCKS = len(_SAFARI_DAILY_LEVEL_PERCENTAGES)


@dataclass(slots=True)
class SafariDailyWorld:
    guild_id: int
    cycle_date: date
    daily_capture_count: int
    daily_unlock_count: int
    current_influence: SafariMapInfluence = field(default_factory=SafariMapInfluence)

    @classmethod
    def create(cls, guild_id: int, cycle_date: date) -> "SafariDailyWorld":
        return cls(
            guild_id=guild_id,
            cycle_date=cycle_date,
            daily_capture_count=0,
            daily_unlock_count=0,
            current_influence=SafariMapInfluence(),
        )

    def __post_init__(self) -> None:
        if self.guild_id <= 0:
            raise ValueError("guild_id must be positive.")

        if self.cycle_date is None:
            raise ValueError("cycle_date is required.")

        if self.daily_capture_count < 0:
            raise ValueError("daily_capture_count cannot be negative.")

        if self.daily_unlock_count < 0:
            raise ValueError("daily_unlock_count cannot be negative.")

        if self.daily_unlock_count > _SAFARI_DAILY_MAX_UNLOCKS:
            raise ValueError("daily_unlock_count cannot exceed five.")


@dataclass(frozen=True, slots=True)
class SafariDailyProgressSnapshot:
    guild_id: int
    cycle_date: date
    active_player_count: int
    effective_active_players: int
    daily_capture_target: int
    daily_capture_count: int
    daily_unlock_count: int
    thresholds: tuple[int, int, int, int, int]
    next_threshold: int | None
    captures_remaining: int
    all_unlocked: bool
    current_influence: SafariMapInfluence


@dataclass(frozen=True, slots=True)
class SafariDailyCaptureResult:
    world: SafariDailyWorld
    snapshot: SafariDailyProgressSnapshot
    created_unlocks: tuple[SafariUnlock, ...]
    newly_reached_levels: tuple[int, ...]


class SafariDailyProgressService:
    def calculate_daily_target(self, active_player_count: int) -> int:
        if active_player_count < 0:
            raise ValueError("active_player_count cannot be negative.")
        return max(active_player_count, 1) * 16

    def calculate_thresholds(
        self,
        daily_capture_target: int,
    ) -> tuple[int, int, int, int, int]:
        if daily_capture_target <= 0:
            raise ValueError("daily_capture_target must be positive.")

        thresholds = tuple(
            ceil(daily_capture_target * percentage)
            for percentage in _SAFARI_DAILY_LEVEL_PERCENTAGES
        )
        return (
            thresholds[0],
            thresholds[1],
            thresholds[2],
            thresholds[3],
            thresholds[4],
        )

    def calculate_reached_levels(
        self,
        daily_capture_count: int,
        thresholds: tuple[int, int, int, int, int],
    ) -> tuple[int, ...]:
        if daily_capture_count < 0:
            raise ValueError("daily_capture_count cannot be negative.")

        return tuple(
            level
            for level, threshold in enumerate(thresholds, start=1)
            if daily_capture_count >= threshold
        )

    def calculate_newly_reached_levels(
        self,
        previous_unlock_count: int,
        daily_capture_count: int,
        thresholds: tuple[int, int, int, int, int],
    ) -> tuple[int, ...]:
        if previous_unlock_count < 0:
            raise ValueError("previous_unlock_count cannot be negative.")

        reached_levels = self.calculate_reached_levels(
            daily_capture_count,
            thresholds,
        )
        return tuple(level for level in reached_levels if level > previous_unlock_count)

    def calculate_next_threshold(
        self,
        daily_unlock_count: int,
        thresholds: tuple[int, int, int, int, int],
    ) -> int | None:
        if daily_unlock_count < 0:
            raise ValueError("daily_unlock_count cannot be negative.")
        if daily_unlock_count >= _SAFARI_DAILY_MAX_UNLOCKS:
            return None
        return thresholds[daily_unlock_count]

    def snapshot(
        self,
        world: SafariDailyWorld,
        active_player_count: int,
    ) -> SafariDailyProgressSnapshot:
        daily_capture_target = self.calculate_daily_target(active_player_count)
        thresholds = self.calculate_thresholds(daily_capture_target)
        next_threshold = self.calculate_next_threshold(
            world.daily_unlock_count,
            thresholds,
        )
        captures_remaining = (
            0
            if next_threshold is None
            else max(0, next_threshold - world.daily_capture_count)
        )

        return SafariDailyProgressSnapshot(
            guild_id=world.guild_id,
            cycle_date=world.cycle_date,
            active_player_count=active_player_count,
            effective_active_players=max(active_player_count, 1),
            daily_capture_target=daily_capture_target,
            daily_capture_count=world.daily_capture_count,
            daily_unlock_count=world.daily_unlock_count,
            thresholds=thresholds,
            next_threshold=next_threshold,
            captures_remaining=captures_remaining,
            all_unlocked=world.daily_unlock_count >= _SAFARI_DAILY_MAX_UNLOCKS,
            current_influence=world.current_influence,
        )

    def register_capture(
        self,
        world: SafariDailyWorld,
        species_types: list[str] | tuple[str, ...],
        captured_at: date | datetime,
        *,
        active_player_count: int,
        progress_amount: int = 1,
    ) -> SafariDailyCaptureResult:
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
        if captured_date < world.cycle_date:
            raise ValueError("captured_at cannot be before the current cycle.")
        if captured_date > world.cycle_date:
            raise ValueError("captured_at cannot be after the current cycle.")

        world.daily_capture_count += progress_amount
        world.current_influence = self._merge_influence(
            world.current_influence,
            normalized_types,
        )

        snapshot = self.snapshot(world, active_player_count)
        newly_reached_levels = self.calculate_newly_reached_levels(
            world.daily_unlock_count,
            world.daily_capture_count,
            snapshot.thresholds,
        )

        created_unlocks = tuple(
            self._build_unlock(
                guild_id=world.guild_id,
                cycle_date=world.cycle_date,
                level=level,
                influence=world.current_influence,
                captured_at=captured_at,
            )
            for level in newly_reached_levels
            if level <= _SAFARI_DAILY_MAX_UNLOCKS
        )

        if newly_reached_levels:
            world.daily_unlock_count = max(
                world.daily_unlock_count,
                max(newly_reached_levels),
            )

        return SafariDailyCaptureResult(
            world=world,
            snapshot=self.snapshot(world, active_player_count),
            created_unlocks=created_unlocks,
            newly_reached_levels=newly_reached_levels,
        )

    @staticmethod
    def _build_unlock(
        *,
        guild_id: int,
        cycle_date: date,
        level: int,
        influence: SafariMapInfluence,
        captured_at: date | datetime,
    ) -> SafariUnlock:
        unlocked_at = (
            captured_at
            if isinstance(captured_at, datetime)
            else datetime.combine(cycle_date, datetime.min.time(), tzinfo=UTC)
        )
        configuration = SAFARI_LEVEL_CONFIGS[level]
        return SafariUnlock(
            id=None,
            guild_id=guild_id,
            level=level,
            encounter_count=configuration.encounter_count,
            balls_per_participant=configuration.balls_per_participant,
            map_influence=SafariMapInfluence(dict(influence.amounts)),
            unlocked_at=unlocked_at,
        )

    @staticmethod
    def _merge_influence(
        current: SafariMapInfluence,
        species_types: tuple[str, ...],
    ) -> SafariMapInfluence:
        amounts = dict(current.amounts)

        for type_name in species_types:
            amounts[type_name] = amounts.get(type_name, 0) + 1

        return SafariMapInfluence(amounts)

    @staticmethod
    def _normalize_type(type_name: str) -> str:
        normalized = type_name.strip().lower()
        if not normalized:
            raise ValueError("species_types cannot contain empty names.")
        return normalized

    @staticmethod
    def _normalize_date(
        captured_at: date | datetime,
    ) -> date:
        if isinstance(captured_at, datetime):
            return captured_at.date()
        return captured_at
