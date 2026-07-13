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
    _COMMON_COMPOSITIONS = frozenset(
        {
            SafariComposition.NORMAL,
            SafariComposition.DUEL,
            SafariComposition.HERD,
            SafariComposition.SOLITARY,
            SafariComposition.BABY_NEST,
        }
    )

    def __init__(
        self,
        species_repository: SpeciesRepository,
        opportunity_factory: OpportunityFactory,
        random_source: random.Random,
    ) -> None:
        self._species_repository = species_repository
        self._opportunity_factory = opportunity_factory
        self._random_source = random_source

    async def generate(
        self,
        context: SafariEncounterContext,
        composition: SafariComposition = SafariComposition.NORMAL,
    ) -> SafariEncounter:
        self._validate_composition(composition)
        catalog = await self._species_repository.get_all()
        return self._generate_from_catalog(context, composition, catalog)

    async def generate_from_compositions(
        self,
        context: SafariEncounterContext,
        compositions: tuple[SafariComposition, ...],
    ) -> SafariEncounter:
        ordered_compositions = tuple(dict.fromkeys(compositions))
        for composition in ordered_compositions:
            self._validate_composition(composition)

        catalog = await self._species_repository.get_all()
        normal_attempted = False
        last_error: SafariEncounterGenerationError | None = None

        for composition in ordered_compositions:
            normal_attempted = (
                normal_attempted or composition == SafariComposition.NORMAL
            )
            try:
                return self._generate_from_catalog(context, composition, catalog)
            except SafariEncounterGenerationError as error:
                last_error = error

        if not normal_attempted:
            try:
                return self._generate_from_catalog(
                    context,
                    SafariComposition.NORMAL,
                    catalog,
                )
            except SafariEncounterGenerationError as error:
                last_error = error

        raise SafariEncounterGenerationError(
            "no common Safari composition can be generated."
        ) from last_error

    def _generate_from_catalog(
        self,
        context: SafariEncounterContext,
        composition: SafariComposition,
        catalog: tuple[Species, ...],
    ) -> SafariEncounter:
        weighted_candidates = [
            (species, self._weight_for(species, context))
            for species in catalog
            if self._is_candidate(species, context)
            and (composition != SafariComposition.BABY_NEST or species.metadata.is_baby)
        ]
        selectable_candidates = [
            (species, weight) for species, weight in weighted_candidates if weight > 0
        ]
        selected_species = self._select_species(
            composition,
            selectable_candidates,
        )
        slots = tuple(
            SafariEncounterSlot(
                id=uuid4(),
                opportunity=self._opportunity_factory.create(species),
            )
            for species in selected_species
        )
        return SafariEncounter(
            id=uuid4(),
            composition=composition,
            slots=slots,
            is_regional_herd=False,
        )

    def _select_species(
        self,
        composition: SafariComposition,
        weighted_candidates: list[tuple[Species, float]],
    ) -> tuple[Species, ...]:
        candidate_count = len(weighted_candidates)
        if composition == SafariComposition.NORMAL:
            self._require_candidates(composition, candidate_count, 1)
            return self._select_without_replacement(
                weighted_candidates,
                min(self._MAX_SLOT_COUNT, candidate_count),
            )
        if composition == SafariComposition.DUEL:
            self._require_candidates(composition, candidate_count, 2)
            return self._select_without_replacement(weighted_candidates, 2)
        if composition == SafariComposition.HERD:
            self._require_candidates(composition, candidate_count, 1)
            species = self._select_without_replacement(weighted_candidates, 1)[0]
            return (species,) * self._random_source.choice((3, 4, 5))
        if composition == SafariComposition.SOLITARY:
            self._require_candidates(composition, candidate_count, 1)
            return self._select_without_replacement(weighted_candidates, 1)

        self._require_candidates(composition, candidate_count, 2)
        target_count = 2 if candidate_count == 2 else self._random_source.choice((2, 3))
        return self._select_without_replacement(weighted_candidates, target_count)

    @staticmethod
    def _require_candidates(
        composition: SafariComposition,
        actual_count: int,
        required_count: int,
    ) -> None:
        if actual_count < required_count:
            raise SafariEncounterGenerationError(
                f"not enough valid Species for Safari composition {composition.value}."
            )

    def _validate_composition(self, composition: SafariComposition) -> None:
        if composition not in self._COMMON_COMPOSITIONS:
            raise SafariEncounterGenerationError(
                f"unsupported Safari composition: {composition.value}."
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
        target_count: int,
    ) -> tuple[Species, ...]:
        available = list(weighted_candidates)
        selected: list[Species] = []

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
