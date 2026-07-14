from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from core.rarity import RARITY_CONFIG
from core.safari.encounter import SafariEncounter, SafariEncounterSlot
from core.safari.participant import SafariParticipant
from core.safari.route import SafariRouteOption
from core.species.regional_species import is_regional_species


class SafariVotePolicy(str, Enum):
    PREFER_ADVANCE = "prefer_advance"
    PREFER_STAY = "prefer_stay"
    RANDOM = "random"


@dataclass(frozen=True, slots=True)
class SafariPlayerStrategy:
    name: str
    ball_mode: str
    slot_mode: str
    vote_policy: SafariVotePolicy

    def choose_slot(
        self,
        encounter: SafariEncounter,
        random_source: random.Random,
    ) -> SafariEncounterSlot:
        slots = encounter.slots
        if not slots:
            raise ValueError("encounter must have at least one slot.")

        if self.slot_mode == "random":
            return random_source.choice(slots)

        scored = [
            (self._slot_score(slot), index, slot) for index, slot in enumerate(slots)
        ]
        reverse = self.slot_mode == "aggressive"
        return sorted(scored, key=lambda item: (item[0], item[1]), reverse=reverse)[0][
            2
        ]

    def choose_balls(
        self,
        participant: SafariParticipant,
        slot: SafariEncounterSlot,
        random_source: random.Random,
    ) -> int:
        available = min(3, participant.remaining_balls)
        if available <= 0:
            raise ValueError("participant has no Safari Balls remaining.")

        if self.ball_mode == "fixed_1":
            return 1
        if self.ball_mode == "fixed_2":
            return min(2, available)
        if self.ball_mode == "fixed_3":
            return min(3, available)
        if self.ball_mode == "random":
            return random_source.randint(1, available)
        if self.ball_mode == "conservative":
            score = self._slot_score(slot)
            if score >= 120:
                return min(3, available)
            if score >= 60:
                return min(2, available)
            return 1
        if self.ball_mode == "aggressive":
            return min(3, available)

        raise ValueError(f"unknown ball mode: {self.ball_mode}")

    def choose_route_option(
        self,
        options: tuple[SafariRouteOption, ...],
        random_source: random.Random,
    ) -> SafariRouteOption:
        if not options:
            raise ValueError("route vote requires at least one option.")

        if self.vote_policy is SafariVotePolicy.RANDOM:
            return random_source.choice(options)
        if self.vote_policy is SafariVotePolicy.PREFER_STAY:
            return next(
                (option for option in options if option.stays_in_same_zone),
                options[0],
            )
        return next(
            (option for option in options if not option.stays_in_same_zone),
            options[0],
        )

    @staticmethod
    def _slot_score(slot: SafariEncounterSlot) -> int:
        species = slot.opportunity.species
        score = 0
        if species.metadata.is_legendary:
            score += 100
        if species.metadata.is_mythical:
            score += 95
        if is_regional_species(species):
            score += 60
        if slot.opportunity.is_shiny:
            score += 40
        if species.metadata.is_baby:
            score += 10
        score += int((1.0 / RARITY_CONFIG[species.spawn_rarity].spawn_weight) * 10)
        return score


DEFAULT_PLAYER_STRATEGIES: tuple[SafariPlayerStrategy, ...] = (
    SafariPlayerStrategy(
        name="conservative",
        ball_mode="conservative",
        slot_mode="conservative",
        vote_policy=SafariVotePolicy.PREFER_STAY,
    ),
    SafariPlayerStrategy(
        name="aggressive",
        ball_mode="aggressive",
        slot_mode="aggressive",
        vote_policy=SafariVotePolicy.PREFER_ADVANCE,
    ),
    SafariPlayerStrategy(
        name="random",
        ball_mode="random",
        slot_mode="random",
        vote_policy=SafariVotePolicy.RANDOM,
    ),
    SafariPlayerStrategy(
        name="fixed_1",
        ball_mode="fixed_1",
        slot_mode="random",
        vote_policy=SafariVotePolicy.PREFER_ADVANCE,
    ),
    SafariPlayerStrategy(
        name="fixed_2",
        ball_mode="fixed_2",
        slot_mode="random",
        vote_policy=SafariVotePolicy.PREFER_ADVANCE,
    ),
    SafariPlayerStrategy(
        name="fixed_3",
        ball_mode="fixed_3",
        slot_mode="random",
        vote_policy=SafariVotePolicy.PREFER_ADVANCE,
    ),
)
