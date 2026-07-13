from __future__ import annotations

import random
from typing import Mapping
from uuid import uuid4

from core.opportunity.opportunity_factory import OpportunityFactory
from core.rarity import RARITY_CONFIG
from core.safari.domain import SafariComposition
from core.safari.encounter import SafariEncounter, SafariEncounterSlot
from core.safari.encounter_context import SafariEncounterContext
from core.species.regional_species import is_regional_species
from core.species.species import Species
from core.species.species_repository import SpeciesRepository


class SafariEncounterGenerationError(ValueError):
    pass


class SafariEncounterGenerator:
    _MAX_SLOT_COUNT = 3

    def __init__(
        self,
        species_repository: SpeciesRepository,
        opportunity_factory: OpportunityFactory,
        random_source: random.Random,
    ) -> None:
        self._species_repository = species_repository
        self._opportunity_factory = opportunity_factory
        self._random_source = random_source

    async def generate(self, context: SafariEncounterContext) -> SafariEncounter:
        catalog = await self._species_repository.get_all()
        weighted_candidates = [
            (species, self._weight_for(species, context))
            for species in catalog
            if self._is_candidate(species, context)
        ]
        selectable_candidates = [
            (species, weight) for species, weight in weighted_candidates if weight > 0
        ]
        if not selectable_candidates:
            raise SafariEncounterGenerationError(
                "no valid Species are available for a normal Safari encounter."
            )

        selected_species = self._select_without_replacement(selectable_candidates)
        slots = tuple(
            SafariEncounterSlot(
                id=uuid4(),
                opportunity=self._opportunity_factory.create(species),
            )
            for species in selected_species
        )
        return SafariEncounter(
            id=uuid4(),
            composition=SafariComposition.NORMAL,
            slots=slots,
            is_regional_herd=False,
        )

    def _is_candidate(
        self,
        species: Species,
        context: SafariEncounterContext,
    ) -> bool:
        return (
            species.id not in context.seen_species_ids
            and not is_regional_species(species)
            and not species.metadata.is_legendary
            and not species.metadata.is_mythical
        )

    def _weight_for(
        self,
        species: Species,
        context: SafariEncounterContext,
    ) -> float:
        rarity_weight = RARITY_CONFIG[species.spawn_rarity].spawn_weight
        if rarity_weight < 0:
            raise SafariEncounterGenerationError(
                "Safari rarity weights cannot be negative."
            )

        return (
            rarity_weight
            * self._modifier_for(
                species,
                context.map_type_weight_modifiers,
            )
            * self._modifier_for(
                species,
                context.zone_type_weight_modifiers,
            )
            * self._modifier_for(
                species,
                context.route_type_weight_modifiers,
            )
        )

    def _select_without_replacement(
        self,
        weighted_candidates: list[tuple[Species, float]],
    ) -> tuple[Species, ...]:
        available = list(weighted_candidates)
        selected: list[Species] = []
        target_count = min(self._MAX_SLOT_COUNT, len(available))

        while len(selected) < target_count:
            candidates = [species for species, _ in available]
            weights = [weight for _, weight in available]
            chosen = self._random_source.choices(
                candidates,
                weights=weights,
                k=1,
            )[0]
            selected.append(chosen)
            available = [
                (species, weight)
                for species, weight in available
                if species.id != chosen.id
            ]

        return tuple(selected)

    @staticmethod
    def _modifier_for(
        species: Species,
        modifiers: Mapping[str, float],
    ) -> float:
        matching_modifiers = [
            modifiers[type_name]
            for type_name in set(species.types)
            if type_name in modifiers
        ]
        return max(matching_modifiers, default=1.0)
