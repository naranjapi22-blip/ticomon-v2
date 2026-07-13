from __future__ import annotations

import random

from core.safari.domain import (
    SAFARI_ZONE_DEFINITIONS,
    SafariMap,
    SafariMapInfluence,
)


class SafariMapSelector:
    _BASE_MAP_WEIGHT = 1.0
    _INFLUENCE_AMOUNT_CAP = 100
    _MAX_INFLUENCE_BONUS = 2.0

    def select(
        self,
        influence: SafariMapInfluence,
        random_source: random.Random,
    ) -> SafariMap:
        maps = tuple(SafariMap)
        weights = tuple(self._weight_for(safari_map, influence) for safari_map in maps)
        if any(weight <= 0 for weight in weights):
            raise ValueError("Safari map weights must be positive.")

        return random_source.choices(maps, weights=weights, k=1)[0]

    def _weight_for(
        self,
        safari_map: SafariMap,
        influence: SafariMapInfluence,
    ) -> float:
        definitions = tuple(
            definition
            for definition in SAFARI_ZONE_DEFINITIONS
            if definition.safari_map == safari_map
        )
        influence_bonus = 0.0

        for type_name, amount in influence.amounts.items():
            if amount == 0:
                continue
            affinity = sum(
                max(definition.base_type_weights.get(type_name, 1.0) - 1.0, 0.0)
                for definition in definitions
            ) / len(definitions)
            capped_amount = min(amount, self._INFLUENCE_AMOUNT_CAP)
            influence_bonus += (capped_amount / self._INFLUENCE_AMOUNT_CAP) * affinity

        return self._BASE_MAP_WEIGHT + min(
            influence_bonus,
            self._MAX_INFLUENCE_BONUS,
        )
