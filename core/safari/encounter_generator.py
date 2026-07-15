from __future__ import annotations

import random
from dataclasses import replace
from typing import Mapping
from uuid import uuid4

from core.opportunity.opportunity_factory import OpportunityFactory
from core.rarity import RARITY_CONFIG
from core.safari.domain import (
    SafariCapturePolicy,
    SafariComposition,
    SafariEncounterStatus,
    SafariPhase,
    SafariRegionalEncounterForm,
    SafariThematicEvent,
)
from core.safari.encounter import (
    SafariEncounter,
    SafariEncounterSlot,
    determine_capture_policy,
)
from core.safari.encounter_context import SafariEncounterContext
from core.safari.event_catalog import (
    EVENT_REQUIRED_TYPES,
    EVENT_WEIGHTS,
    available_events_for,
    available_extraordinary_events_for,
    available_regional_events_for,
)
from core.safari.generated_encounter import SafariGeneratedEncounter
from core.safari.regional_encounter import SafariGeneratedRegionalEncounter
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
        return self._generate_from_catalog(
            context,
            composition,
            catalog,
            SafariThematicEvent.NONE,
        )

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
                return self._generate_from_catalog(
                    context,
                    composition,
                    catalog,
                    SafariThematicEvent.NONE,
                )
            except SafariEncounterGenerationError as error:
                last_error = error

        if not normal_attempted:
            try:
                return self._generate_from_catalog(
                    context,
                    SafariComposition.NORMAL,
                    catalog,
                    SafariThematicEvent.NONE,
                )
            except SafariEncounterGenerationError as error:
                last_error = error

        raise SafariEncounterGenerationError(
            "no common Safari composition can be generated."
        ) from last_error

    async def generate_with_events(
        self,
        context: SafariEncounterContext,
        compositions: tuple[SafariComposition, ...],
    ) -> SafariGeneratedEncounter:
        ordered_compositions = tuple(dict.fromkeys(compositions))
        for composition in ordered_compositions:
            self._validate_composition(composition)

        catalog = await self._species_repository.get_all()
        attempted: set[tuple[SafariComposition, SafariThematicEvent]] = set()
        last_error: SafariEncounterGenerationError | None = None

        for composition in ordered_compositions:
            events = self._event_attempt_order(
                self._events_for_context(
                    context, available_events_for(context, composition)
                )
            )
            for event in events:
                attempted.add((composition, event))
                try:
                    encounter = self._generate_from_catalog(
                        context,
                        composition,
                        catalog,
                        event,
                    )
                    return SafariGeneratedEncounter(encounter, event)
                except SafariEncounterGenerationError as error:
                    last_error = error

        fallback = (SafariComposition.NORMAL, SafariThematicEvent.NONE)
        if self._event_is_required(context):
            raise SafariEncounterGenerationError(
                "Safari event quota cannot be satisfied by the available candidates."
            ) from last_error
        if fallback not in attempted:
            try:
                encounter = self._generate_from_catalog(
                    context,
                    SafariComposition.NORMAL,
                    catalog,
                    SafariThematicEvent.NONE,
                )
                return SafariGeneratedEncounter(encounter, SafariThematicEvent.NONE)
            except SafariEncounterGenerationError as error:
                last_error = error

        raise SafariEncounterGenerationError(
            "no Safari event and composition combination can be generated."
        ) from last_error

    async def generate_regional(
        self,
        context: SafariEncounterContext,
        regional_form: SafariRegionalEncounterForm,
        event: SafariThematicEvent = SafariThematicEvent.NONE,
    ) -> SafariGeneratedRegionalEncounter:
        self._validate_regional_request(context, regional_form)
        if event not in available_regional_events_for(context):
            raise SafariEncounterGenerationError(
                "Safari event is not available for this regional encounter."
            )

        catalog = await self._species_repository.get_all()
        encounter = self._generate_regional_from_catalog(
            context,
            regional_form,
            catalog,
            event,
        )
        return SafariGeneratedRegionalEncounter(encounter, event, regional_form)

    async def generate_regional_with_events(
        self,
        context: SafariEncounterContext,
        regional_forms: tuple[SafariRegionalEncounterForm, ...],
    ) -> SafariGeneratedRegionalEncounter:
        ordered_forms = tuple(dict.fromkeys(regional_forms))
        if not ordered_forms:
            raise SafariEncounterGenerationError(
                "at least one regional encounter form is required."
            )
        for regional_form in ordered_forms:
            self._validate_regional_request(context, regional_form)

        catalog = await self._species_repository.get_all()
        last_error: SafariEncounterGenerationError | None = None
        for regional_form in ordered_forms:
            events = self._event_attempt_order(
                self._events_for_context(
                    context, available_regional_events_for(context)
                )
            )
            for event in events:
                try:
                    encounter = self._generate_regional_from_catalog(
                        context,
                        regional_form,
                        catalog,
                        event,
                    )
                    return SafariGeneratedRegionalEncounter(
                        encounter,
                        event,
                        regional_form,
                    )
                except SafariEncounterGenerationError as error:
                    last_error = error

        raise SafariEncounterGenerationError(
            "no regional Safari encounter can be generated."
        ) from last_error

    async def generate_legendary(
        self,
        context: SafariEncounterContext,
        event: SafariThematicEvent = SafariThematicEvent.NONE,
    ) -> SafariGeneratedEncounter:
        return await self._generate_extraordinary(
            context,
            SafariComposition.LEGENDARY,
            event,
        )

    async def generate_mythical(
        self,
        context: SafariEncounterContext,
        event: SafariThematicEvent = SafariThematicEvent.NONE,
    ) -> SafariGeneratedEncounter:
        return await self._generate_extraordinary(
            context,
            SafariComposition.MYTHICAL,
            event,
        )

    async def generate_extraordinary_with_events(
        self,
        context: SafariEncounterContext,
        compositions: tuple[SafariComposition, ...],
    ) -> SafariGeneratedEncounter:
        ordered_compositions = tuple(dict.fromkeys(compositions))
        if not ordered_compositions:
            raise SafariEncounterGenerationError(
                "at least one extraordinary composition is required."
            )
        for composition in ordered_compositions:
            if composition not in (
                SafariComposition.LEGENDARY,
                SafariComposition.MYTHICAL,
            ):
                raise ValueError("composition must be LEGENDARY or MYTHICAL.")
        if context.phase != SafariPhase.FINAL:
            raise SafariEncounterGenerationError(
                "extraordinary encounters are only available during FINAL."
            )

        catalog = await self._species_repository.get_all()
        last_error: SafariEncounterGenerationError | None = None
        for composition in ordered_compositions:
            try:
                self._validate_extraordinary_request(context, composition)
            except SafariEncounterGenerationError as error:
                last_error = error
                continue
            events = self._event_attempt_order(
                self._events_for_context(
                    context, available_extraordinary_events_for(context, composition)
                )
            )
            for event in events:
                try:
                    encounter = self._generate_extraordinary_from_catalog(
                        context,
                        composition,
                        catalog,
                        event,
                    )
                    return SafariGeneratedEncounter(encounter, event)
                except SafariEncounterGenerationError as error:
                    last_error = error

        raise SafariEncounterGenerationError(
            "no extraordinary Safari encounter can be generated."
        ) from last_error

    def apply_global_shiny(
        self,
        context: SafariEncounterContext,
        generated: (
            SafariEncounter
            | SafariGeneratedEncounter
            | SafariGeneratedRegionalEncounter
        ),
    ) -> SafariEncounter | SafariGeneratedEncounter | SafariGeneratedRegionalEncounter:
        if context.phase != SafariPhase.FINAL:
            raise SafariEncounterGenerationError(
                "global shiny encounters are only available during FINAL."
            )
        if context.extraordinary_flags.shiny_encounter_seen:
            raise SafariEncounterGenerationError(
                "the global shiny encounter was already seen."
            )

        encounter = (
            generated.encounter if hasattr(generated, "encounter") else generated
        )
        if (
            encounter.status != SafariEncounterStatus.OPEN
            or encounter.eligible_participant_ids
        ):
            raise SafariEncounterGenerationError(
                "global shiny must be applied before publishing the encounter."
            )
        shiny_encounter = self._copy_encounter_as_shiny(encounter)

        if isinstance(generated, SafariGeneratedRegionalEncounter):
            return SafariGeneratedRegionalEncounter(
                shiny_encounter,
                generated.event,
                generated.regional_form,
            )
        if isinstance(generated, SafariGeneratedEncounter):
            return SafariGeneratedEncounter(shiny_encounter, generated.event)
        return shiny_encounter

    async def _generate_extraordinary(
        self,
        context: SafariEncounterContext,
        composition: SafariComposition,
        event: SafariThematicEvent,
    ) -> SafariGeneratedEncounter:
        self._validate_extraordinary_request(context, composition)
        if event not in available_extraordinary_events_for(context, composition):
            raise SafariEncounterGenerationError(
                "Safari event is not available for this extraordinary encounter."
            )
        catalog = await self._species_repository.get_all()
        encounter = self._generate_extraordinary_from_catalog(
            context,
            composition,
            catalog,
            event,
        )
        return SafariGeneratedEncounter(encounter, event)

    def _generate_from_catalog(
        self,
        context: SafariEncounterContext,
        composition: SafariComposition,
        catalog: tuple[Species, ...],
        event: SafariThematicEvent,
    ) -> SafariEncounter:
        weighted_candidates = [
            (species, self._weight_for(species, context, event))
            for species in catalog
            if self._is_candidate(species, context, event)
            and (composition != SafariComposition.BABY_NEST or species.metadata.is_baby)
        ]
        selectable_candidates = [
            (species, weight) for species, weight in weighted_candidates if weight > 0
        ]
        selected_species = self._select_species(
            composition,
            selectable_candidates,
        )
        return self._build_encounter(
            selected_species,
            composition,
            is_regional_herd=False,
            event=event,
        )

    def _generate_regional_from_catalog(
        self,
        context: SafariEncounterContext,
        regional_form: SafariRegionalEncounterForm,
        catalog: tuple[Species, ...],
        event: SafariThematicEvent,
    ) -> SafariEncounter:
        regional_candidates = [
            (species, self._weight_for(species, context, event))
            for species in catalog
            if self._is_regional_candidate(species, context, event)
        ]
        selectable_regional = [
            (species, weight) for species, weight in regional_candidates if weight > 0
        ]
        self._require_regional_candidates(selectable_regional)
        regional = self._select_without_replacement(selectable_regional, 1)[0]

        if regional_form == SafariRegionalEncounterForm.MIXED:
            ordinary_candidates = [
                (species, self._weight_for(species, context, event))
                for species in catalog
                if self._is_candidate(species, context, event)
                and species.id != regional.id
            ]
            selectable_ordinary = [
                (species, weight)
                for species, weight in ordinary_candidates
                if weight > 0
            ]
            if not selectable_ordinary:
                raise SafariEncounterGenerationError(
                    "regional mixed encounter requires an ordinary Species."
                )
            ordinary = self._select_without_replacement(
                selectable_ordinary,
                min(2, len(selectable_ordinary)),
            )
            selected_species = (regional, *ordinary)
        elif regional_form == SafariRegionalEncounterForm.HERD:
            selected_species = (regional,)
        else:
            selected_species = (regional,)

        return self._build_encounter(
            selected_species,
            SafariComposition.REGIONAL,
            is_regional_herd=regional_form == SafariRegionalEncounterForm.HERD,
            event=event,
        )

    def _generate_extraordinary_from_catalog(
        self,
        context: SafariEncounterContext,
        composition: SafariComposition,
        catalog: tuple[Species, ...],
        event: SafariThematicEvent,
    ) -> SafariEncounter:
        weighted_candidates = [
            (species, self._weight_for(species, context, event))
            for species in catalog
            if self._is_extraordinary_candidate(
                species,
                context,
                composition,
                event,
            )
        ]
        selectable = [
            (species, weight) for species, weight in weighted_candidates if weight > 0
        ]
        if not selectable:
            raise SafariEncounterGenerationError(
                f"no valid {composition.value} Species are available."
            )
        selected = self._select_without_replacement(selectable, 1)
        return self._build_encounter(
            selected,
            composition,
            is_regional_herd=False,
            event=event,
        )

    def _build_encounter(
        self,
        selected_species: tuple[Species, ...],
        composition: SafariComposition,
        *,
        is_regional_herd: bool,
        event: SafariThematicEvent = SafariThematicEvent.NONE,
    ) -> SafariEncounter:
        slots = tuple(self._build_slot(species) for species in selected_species)
        return SafariEncounter(
            id=uuid4(),
            composition=composition,
            slots=slots,
            is_regional_herd=is_regional_herd,
            event=event,
        )

    def _build_slot(self, species: Species) -> SafariEncounterSlot:
        opportunity = self._opportunity_factory.create(species)
        return SafariEncounterSlot(
            id=uuid4(),
            opportunity=opportunity,
            capture_policy=determine_capture_policy(opportunity),
        )

    @staticmethod
    def _copy_encounter_as_shiny(encounter: SafariEncounter) -> SafariEncounter:
        slots = tuple(
            SafariEncounterSlot(
                id=slot.id,
                opportunity=replace(slot.opportunity, is_shiny=True),
                capture_policy=SafariCapturePolicy.UNIQUE,
            )
            for slot in encounter.slots
        )
        return SafariEncounter(
            id=encounter.id,
            composition=encounter.composition,
            slots=slots,
            is_regional_herd=encounter.is_regional_herd,
            event=encounter.event,
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
            return (species,)
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

    @staticmethod
    def _validate_regional_request(
        context: SafariEncounterContext,
        regional_form: SafariRegionalEncounterForm,
    ) -> None:
        if context.phase == SafariPhase.START:
            raise SafariEncounterGenerationError(
                "regional encounters are not available during START."
            )
        if not isinstance(regional_form, SafariRegionalEncounterForm):
            raise ValueError("regional_form must be a SafariRegionalEncounterForm.")

    @staticmethod
    def _validate_extraordinary_request(
        context: SafariEncounterContext,
        composition: SafariComposition,
    ) -> None:
        if composition not in (
            SafariComposition.LEGENDARY,
            SafariComposition.MYTHICAL,
        ):
            raise ValueError("composition must be LEGENDARY or MYTHICAL.")
        if context.phase != SafariPhase.FINAL:
            raise SafariEncounterGenerationError(
                "extraordinary encounters are only available during FINAL."
            )
        flags = context.extraordinary_flags
        if composition == SafariComposition.LEGENDARY and flags.legendary_seen:
            raise SafariEncounterGenerationError(
                "the legendary encounter was already seen."
            )
        if composition == SafariComposition.MYTHICAL and flags.mythical_seen:
            raise SafariEncounterGenerationError(
                "the mythical encounter was already seen."
            )

    @staticmethod
    def _require_regional_candidates(
        candidates: list[tuple[Species, float]],
    ) -> None:
        if not candidates:
            raise SafariEncounterGenerationError(
                "no valid regional Species are available."
            )

    def _is_candidate(
        self,
        species: Species,
        context: SafariEncounterContext,
        event: SafariThematicEvent,
    ) -> bool:
        return (
            self._passes_base_filters(species, context)
            and not is_regional_species(species)
            and self._event_allows_species(species, event)
        )

    def _is_regional_candidate(
        self,
        species: Species,
        context: SafariEncounterContext,
        event: SafariThematicEvent,
    ) -> bool:
        return (
            self._passes_base_filters(species, context)
            and is_regional_species(species)
            and self._event_allows_species(species, event)
        )

    def _is_extraordinary_candidate(
        self,
        species: Species,
        context: SafariEncounterContext,
        composition: SafariComposition,
        event: SafariThematicEvent,
    ) -> bool:
        if species.id in context.seen_species_ids or is_regional_species(species):
            return False
        metadata = species.metadata
        if composition == SafariComposition.LEGENDARY:
            matches_composition = metadata.is_legendary and not metadata.is_mythical
        else:
            matches_composition = metadata.is_mythical and not metadata.is_legendary
        return matches_composition and self._event_allows_species(species, event)

    @staticmethod
    def _passes_base_filters(
        species: Species,
        context: SafariEncounterContext,
    ) -> bool:
        return (
            species.id not in context.seen_species_ids
            and not species.metadata.is_legendary
            and not species.metadata.is_mythical
        )

    @staticmethod
    def _event_allows_species(
        species: Species,
        event: SafariThematicEvent,
    ) -> bool:
        required_types = EVENT_REQUIRED_TYPES[event]
        return not required_types or not required_types.isdisjoint(species.types)

    def _weight_for(
        self,
        species: Species,
        context: SafariEncounterContext,
        event: SafariThematicEvent,
    ) -> float:
        rarity_weight = RARITY_CONFIG[species.spawn_rarity].spawn_weight
        if rarity_weight < 0:
            raise ValueError("Safari rarity weights cannot be negative.")

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

    @staticmethod
    def _event_is_required(context: SafariEncounterContext) -> bool:
        missing = context.event_quota - context.generated_event_count
        return context.event_quota > 0 and context.encounters_remaining <= missing

    @classmethod
    def _events_for_context(
        cls,
        context: SafariEncounterContext,
        events: frozenset[SafariThematicEvent],
    ) -> frozenset[SafariThematicEvent]:
        if not cls._event_is_required(context):
            fresh_events = frozenset(
                event
                for event in events
                if event is not SafariThematicEvent.NONE
                and event not in context.generated_event_types
            )
            if fresh_events:
                return fresh_events | (
                    {SafariThematicEvent.NONE}
                    if SafariThematicEvent.NONE in events
                    else set()
                )
            return events

        required_events = frozenset(
            event for event in events if event is not SafariThematicEvent.NONE
        )
        fresh_events = frozenset(
            event
            for event in required_events
            if event not in context.generated_event_types
        )
        return fresh_events or required_events

    def _event_attempt_order(
        self,
        events: frozenset[SafariThematicEvent],
    ) -> tuple[SafariThematicEvent, ...]:
        available = sorted(events, key=lambda event: event.value)
        ordered: list[SafariThematicEvent] = []

        while available:
            weights = [EVENT_WEIGHTS[event] for event in available]
            if any(weight <= 0 for weight in weights):
                raise ValueError("Safari event weights must be positive.")
            selected = self._random_source.choices(
                available,
                weights=weights,
                k=1,
            )[0]
            ordered.append(selected)
            available.remove(selected)

        return tuple(ordered)

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
        if not matching_modifiers:
            return 1.0

        modifier = 1.0
        for value in matching_modifiers:
            modifier *= value
        return modifier
