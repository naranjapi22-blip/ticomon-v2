from __future__ import annotations

import random
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from datetime import date, datetime
from enum import Enum
from typing import Iterable
from uuid import UUID

from core.candy.candy_inventory import CandyInventory
from core.capture.application.capture_unit_of_work import (
    CaptureTransaction,
    CaptureUnitOfWork,
)
from core.creature.creature import Creature
from core.opportunity.opportunity_factory import OpportunityFactory
from core.rarity import Rarity
from core.safari.domain import (
    SafariComposition,
    SafariPhase,
    SafariRegionalEncounterForm,
    SafariUnlockStatus,
)
from core.safari.encounter_context import SafariEncounterContext
from core.safari.encounter_generator import (
    SafariEncounterGenerationError,
    SafariEncounterGenerator,
)
from core.safari.generated_encounter import SafariGeneratedEncounter
from core.safari.regional_encounter import SafariGeneratedRegionalEncounter
from core.safari.unlock import SafariUnlock
from core.safari.unlock_repository import SafariUnlockRepository
from core.species.species import Species
from core.species.species_repository import SpeciesRepository

COMMON_COMPOSITIONS: tuple[SafariComposition, ...] = (
    SafariComposition.NORMAL,
    SafariComposition.DUEL,
    SafariComposition.HERD,
    SafariComposition.SOLITARY,
    SafariComposition.BABY_NEST,
)

REGIONAL_FORMS: tuple[SafariRegionalEncounterForm, ...] = (
    SafariRegionalEncounterForm.MIXED,
    SafariRegionalEncounterForm.SOLITARY,
    SafariRegionalEncounterForm.HERD,
)


class CatalogSource(str, Enum):
    AUTO = "auto"
    NEON = "neon"
    CSV = "csv"


class CachedSpeciesRepository(SpeciesRepository):
    def __init__(self, species: Iterable[Species]) -> None:
        self._species = tuple(species)

    async def get(self, species_id: int) -> Species:
        for species in self._species:
            if species.id == species_id:
                return species
        raise ValueError(f"Species with id {species_id} was not found.")

    async def find_by_name(self, name: str) -> Species | None:
        for species in self._species:
            if species.name == name:
                return species
        return None

    async def get_all(self) -> tuple[Species, ...]:
        return self._species

    async def find_by_spawn_rarity(self, rarity: Rarity) -> tuple[Species, ...]:
        return tuple(
            species for species in self._species if species.spawn_rarity == rarity
        )

    async def get_many(self, species_ids: list[int] | tuple[int, ...]) -> list[Species]:
        species_by_id = {species.id: species for species in self._species}
        return [species_by_id[species_id] for species_id in species_ids]


class InMemorySafariUnlockRepository(SafariUnlockRepository):
    def __init__(self, unlocks: Iterable[SafariUnlock] = ()) -> None:
        self._unlocks: dict[int, list[SafariUnlock]] = {}
        for unlock in unlocks:
            self._unlocks.setdefault(unlock.guild_id, []).append(unlock)

    async def save(self, unlock: SafariUnlock) -> SafariUnlock:
        self._unlocks.setdefault(unlock.guild_id, []).append(unlock)
        return unlock

    async def get_available_by_guild_id(
        self, guild_id: int
    ) -> tuple[SafariUnlock, ...]:
        unlocks = self._unlocks.get(guild_id, [])
        return tuple(
            sorted(
                (
                    unlock
                    for unlock in unlocks
                    if unlock.status is SafariUnlockStatus.AVAILABLE
                ),
                key=lambda unlock: (unlock.unlocked_at, unlock.id or 0),
            )
        )

    async def consume_next(
        self,
        guild_id: int,
        consumed_at: datetime,
        consumed_session_id: UUID,
    ) -> SafariUnlock | None:
        available = await self.get_available_by_guild_id(guild_id)
        if not available:
            return None
        return await self.consume(
            available[0].id or 0,
            guild_id,
            consumed_at,
            consumed_session_id,
        )

    async def consume(
        self,
        unlock_id: int,
        guild_id: int,
        consumed_at: datetime,
        consumed_session_id: UUID,
    ) -> SafariUnlock | None:
        if unlock_id <= 0:
            raise ValueError("unlock_id must be positive.")

        for unlock in self._unlocks.get(guild_id, []):
            if (
                unlock.id != unlock_id
                or unlock.status is not SafariUnlockStatus.AVAILABLE
            ):
                continue
            unlock.consume(consumed_at, consumed_session_id)
            return unlock
        return None


class InMemoryCaptureTransaction(CaptureTransaction):
    def __init__(self) -> None:
        self._next_creature_id = 1
        self._next_collection_by_trainer: dict[int, int] = {}
        self.saved_creatures: list[Creature] = []
        self.candy_inventories: dict[int, CandyInventory] = {}

    async def save_creature(self, creature: Creature) -> Creature:
        collection_number = (
            self._next_collection_by_trainer.get(creature.trainer_id, 0) + 1
        )
        self._next_collection_by_trainer[creature.trainer_id] = collection_number
        saved = replace(
            creature,
            id=self._next_creature_id,
            collection_number=collection_number,
        )
        self._next_creature_id += 1
        self.saved_creatures.append(saved)
        return saved

    async def get_candy_inventory(self, trainer_id: int) -> CandyInventory:
        return self.candy_inventories.setdefault(trainer_id, CandyInventory())

    async def save_candy_inventory(
        self, trainer_id: int, inventory: CandyInventory
    ) -> None:
        self.candy_inventories[trainer_id] = inventory

    async def get_or_create_world(
        self, guild_id: int, reset_date: date
    ):  # pragma: no cover - unused in simulation
        raise NotImplementedError("World persistence is not used in Safari simulation.")

    async def save_world(self, world):  # pragma: no cover - unused in simulation
        raise NotImplementedError("World persistence is not used in Safari simulation.")

    async def save_unlock(
        self, unlock: SafariUnlock
    ) -> SafariUnlock:  # pragma: no cover - unused in simulation
        raise NotImplementedError(
            "Unlock persistence is not used in Safari simulation."
        )


class InMemoryCaptureUnitOfWork(CaptureUnitOfWork):
    def __init__(self, transaction: InMemoryCaptureTransaction | None = None) -> None:
        self.transaction_state = transaction or InMemoryCaptureTransaction()

    @asynccontextmanager
    async def transaction(self):
        yield self.transaction_state


@dataclass(frozen=True, slots=True)
class SimulationGenerationOutcome:
    generated: SafariGeneratedEncounter | SafariGeneratedRegionalEncounter
    plan_kind: str
    composition_fallbacks: int = 0
    event_fallbacks: int = 0
    normal_fallbacks: int = 0
    global_shiny_applied: bool = False


@dataclass(frozen=True, slots=True)
class SimulationGenerationPlan:
    kind: str
    compositions: tuple[SafariComposition, ...] = ()
    regional_forms: tuple[SafariRegionalEncounterForm, ...] = ()
    global_shiny_chance: float = 0.0

    async def execute(
        self,
        generator: SafariEncounterGenerator,
        context: SafariEncounterContext,
        random_source: random.Random,
    ) -> SimulationGenerationOutcome:
        if self.kind == "common":
            generated = await SafariEncounterGenerator.generate_with_events(
                generator,
                context,
                self.compositions or COMMON_COMPOSITIONS,
            )
            return await self._apply_global_shiny(
                generator,
                context,
                random_source,
                generated,
                composition_fallbacks=int(
                    bool(self.compositions)
                    and generated.encounter.composition != self.compositions[0]
                ),
            )

        if self.kind == "regional":
            try:
                generated = (
                    await SafariEncounterGenerator.generate_regional_with_events(
                        generator,
                        context,
                        self.regional_forms or REGIONAL_FORMS,
                    )
                )
            except SafariEncounterGenerationError:
                generated = await SafariEncounterGenerator.generate_with_events(
                    generator,
                    context,
                    (SafariComposition.NORMAL,),
                )
                return await self._apply_global_shiny(
                    generator,
                    context,
                    random_source,
                    generated,
                    composition_fallbacks=1,
                    event_fallbacks=1,
                    normal_fallbacks=1,
                )
            return await self._apply_global_shiny(
                generator,
                context,
                random_source,
                generated,
                composition_fallbacks=int(
                    generated.encounter.composition != SafariComposition.REGIONAL
                ),
            )

        if self.kind in {"legendary", "mythical"}:
            target = (
                SafariComposition.LEGENDARY
                if self.kind == "legendary"
                else SafariComposition.MYTHICAL
            )
            try:
                generated = (
                    await SafariEncounterGenerator.generate_extraordinary_with_events(
                        generator,
                        context,
                        (target,),
                    )
                )
            except SafariEncounterGenerationError:
                generated = await SafariEncounterGenerator.generate_with_events(
                    generator,
                    context,
                    (SafariComposition.NORMAL,),
                )
                return await self._apply_global_shiny(
                    generator,
                    context,
                    random_source,
                    generated,
                    composition_fallbacks=1,
                    event_fallbacks=1,
                    normal_fallbacks=1,
                )
            return await self._apply_global_shiny(
                generator,
                context,
                random_source,
                generated,
                composition_fallbacks=int(generated.encounter.composition != target),
            )

        raise ValueError(f"unknown simulation plan kind: {self.kind}")

    async def _apply_global_shiny(
        self,
        generator: SafariEncounterGenerator,
        context: SafariEncounterContext,
        random_source: random.Random,
        generated: SafariGeneratedEncounter | SafariGeneratedRegionalEncounter,
        *,
        composition_fallbacks: int = 0,
        event_fallbacks: int = 0,
        normal_fallbacks: int = 0,
    ) -> SimulationGenerationOutcome:
        global_shiny_applied = False
        if (
            self.global_shiny_chance > 0
            and context.phase is SafariPhase.FINAL
            and not context.extraordinary_flags.shiny_encounter_seen
            and random_source.random() < self.global_shiny_chance
        ):
            generated = generator.apply_global_shiny(context, generated)
            global_shiny_applied = True

        return SimulationGenerationOutcome(
            generated=generated,
            plan_kind=self.kind,
            composition_fallbacks=composition_fallbacks,
            event_fallbacks=event_fallbacks,
            normal_fallbacks=normal_fallbacks,
            global_shiny_applied=global_shiny_applied,
        )


@dataclass(frozen=True, slots=True)
class SimulationGenerationRecord:
    context: SafariEncounterContext
    outcome: SimulationGenerationOutcome


class SafariSimulationRecorder:
    def __init__(
        self,
        random_source: random.Random,
        *,
        global_shiny_chance: float = 0.001,
    ) -> None:
        self._random_source = random_source
        self._global_shiny_chance = global_shiny_chance
        self._records: dict[UUID, SimulationGenerationRecord] = {}

    def choose_plan(self, context: SafariEncounterContext) -> SimulationGenerationPlan:
        candidates: list[tuple[str, float]] = [("common", 0.7)]
        if context.phase is not SafariPhase.START:
            candidates.append(("regional", 0.2))
        if context.phase is SafariPhase.FINAL:
            if not context.extraordinary_flags.legendary_seen:
                candidates.append(("legendary", 0.06))
            if not context.extraordinary_flags.mythical_seen:
                candidates.append(("mythical", 0.04))

        total_weight = sum(weight for _, weight in candidates)
        roll = self._random_source.random() * total_weight
        cursor = 0.0
        chosen = candidates[0][0]
        for kind, weight in candidates:
            cursor += weight
            if roll <= cursor:
                chosen = kind
                break

        if chosen == "common":
            compositions = list(COMMON_COMPOSITIONS)
            self._random_source.shuffle(compositions)
            return SimulationGenerationPlan(
                kind="common",
                compositions=tuple(compositions),
                global_shiny_chance=self._global_shiny_chance,
            )
        if chosen == "regional":
            forms = list(REGIONAL_FORMS)
            self._random_source.shuffle(forms)
            return SimulationGenerationPlan(
                kind="regional",
                regional_forms=tuple(forms),
                global_shiny_chance=self._global_shiny_chance,
            )
        if chosen in {"legendary", "mythical"}:
            return SimulationGenerationPlan(
                kind=chosen,
                global_shiny_chance=self._global_shiny_chance,
            )

        return SimulationGenerationPlan(
            kind="common",
            compositions=COMMON_COMPOSITIONS,
            global_shiny_chance=self._global_shiny_chance,
        )

    def record_generation(
        self,
        *,
        context: SafariEncounterContext,
        outcome: SimulationGenerationOutcome,
    ) -> None:
        encounter_id = outcome.generated.encounter.id
        self._records[encounter_id] = SimulationGenerationRecord(
            context=context,
            outcome=outcome,
        )

    def consume_generation(self, encounter_id: UUID) -> SimulationGenerationRecord:
        return self._records.pop(encounter_id)

    def peek_generation(self, encounter_id: UUID) -> SimulationGenerationRecord | None:
        return self._records.get(encounter_id)


class SimulationEncounterGenerator(SafariEncounterGenerator):
    def __init__(
        self,
        species_repository: SpeciesRepository,
        opportunity_factory: OpportunityFactory,
        random_source: random.Random,
        recorder: SafariSimulationRecorder,
    ) -> None:
        super().__init__(species_repository, opportunity_factory, random_source)
        self._recorder = recorder
        self._random_source = random_source

    async def generate_with_events(self, context: SafariEncounterContext, compositions):
        return await self._generate(context)

    async def generate_regional_with_events(
        self, context: SafariEncounterContext, regional_forms
    ):
        return await self._generate(context)

    async def generate_legendary(self, context: SafariEncounterContext, event=None):
        return await self._generate(context)

    async def generate_mythical(self, context: SafariEncounterContext, event=None):
        return await self._generate(context)

    async def generate_extraordinary_with_events(
        self, context: SafariEncounterContext, compositions
    ):
        return await self._generate(context)

    async def _generate(self, context: SafariEncounterContext):
        plan = self._recorder.choose_plan(context)
        outcome = await plan.execute(self, context, self._random_source)
        self._recorder.record_generation(context=context, outcome=outcome)
        return outcome.generated
