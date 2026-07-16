from dataclasses import dataclass, replace

from core.collection.catalog import (
    COLLECTIONS,
    CollectionDefinition,
    CollectionEntryDefinition,
    CollectionMilestone,
    calculate_progress,
    collection_by_id,
)
from core.creature.creature_factory import CreatureFactory
from core.opportunity.opportunity_factory import OpportunityFactory


@dataclass(frozen=True, slots=True)
class CollectionEntryStatus:
    definition: CollectionEntryDefinition
    species: object
    variant: object | None
    historically_obtained: bool
    currently_owned: bool
    source: str | None = None
    collection_number: int | None = None

    @property
    def identity(self) -> tuple[int, int | None]:
        return self.species.id, self.variant.id if self.variant is not None else None

    @property
    def collected(self) -> bool:
        return self.historically_obtained


@dataclass(frozen=True, slots=True)
class CollectionAlbum:
    definition: CollectionDefinition
    entries: tuple[CollectionEntryStatus, ...]
    progress: object
    claimed_milestones: frozenset[int]

    @property
    def available_milestones(self) -> tuple[CollectionMilestone, ...]:
        return tuple(
            milestone
            for milestone in self.definition.milestones
            if milestone.threshold <= self.progress.collected_count
            and milestone.threshold <= self.progress.owned_count
            and milestone.threshold not in self.claimed_milestones
        )


@dataclass(frozen=True, slots=True)
class CollectionClaimResult:
    album: CollectionAlbum
    milestone: CollectionMilestone
    claimed: bool


class CollectionApplicationService:
    def __init__(
        self,
        species_repository,
        history_repository,
        creature_repository,
    ) -> None:
        self._species_repository = species_repository
        self._history_repository = history_repository
        self._creature_repository = creature_repository

    async def albums(self, trainer_id: int) -> tuple[CollectionAlbum, ...]:
        history = await self._history_repository.entries_for_trainer(trainer_id)
        claimed = await self._history_repository.claimed_milestones(trainer_id)
        owned = await self._owned_entry_collection_numbers(trainer_id)
        species_by_name = await self._collection_species_by_name(COLLECTIONS)
        albums = []
        for definition in COLLECTIONS:
            albums.append(
                await self._album_from_history(
                    definition,
                    history,
                    owned,
                    claimed,
                    species_by_name,
                )
            )
        return tuple(albums)

    async def album(self, trainer_id: int, collection_id: str) -> CollectionAlbum:
        history = await self._history_repository.entries_for_trainer(trainer_id)
        claimed = await self._history_repository.claimed_milestones(trainer_id)
        owned = await self._owned_entry_collection_numbers(trainer_id)
        definition = collection_by_id(collection_id)
        return await self._album_from_history(
            definition,
            history,
            owned,
            claimed,
            await self._collection_species_by_name((definition,)),
        )

    async def claim(
        self,
        trainer_id: int,
        collection_id: str,
        milestone_threshold: int,
    ) -> CollectionClaimResult:
        album = await self.album(trainer_id, collection_id)
        milestone = next(
            (
                item
                for item in album.definition.milestones
                if item.threshold == milestone_threshold
            ),
            None,
        )
        if milestone is None:
            raise ValueError("Collection milestone was not found.")
        if milestone.threshold > album.progress.collected_count:
            raise ValueError("Collection milestone is not complete.")
        if milestone.threshold > album.progress.owned_count:
            raise ValueError(
                "Collect the required entries in your current collection first."
            )
        if milestone.threshold in album.claimed_milestones:
            return CollectionClaimResult(album, milestone, False)

        claimed = await self._history_repository.claim(
            trainer_id,
            str(album.definition.id),
            milestone.threshold,
            tuple(entry.identity for entry in album.entries),
            milestone.candies,
            milestone.mints,
        )
        return CollectionClaimResult(
            await self.album(trainer_id, collection_id), milestone, claimed
        )

    @staticmethod
    def preview_creature(entry: CollectionEntryStatus):
        opportunity = OpportunityFactory.create(entry.species)
        opportunity = replace(
            opportunity,
            is_shiny=False,
            initial_form=entry.variant,
        )
        return CreatureFactory.create(0, opportunity)

    async def _album_from_history(
        self,
        definition: CollectionDefinition,
        history,
        owned,
        claimed: frozenset[tuple[str, int]],
        species_by_name: dict[str, object],
    ) -> CollectionAlbum:
        obtained = frozenset(entry.identity for entry in history)
        source_by_identity = {entry.identity: entry.source.value for entry in history}
        statuses = []
        for entry in definition.entries:
            statuses.append(
                self._resolve_entry(
                    entry,
                    obtained,
                    owned,
                    source_by_identity,
                    species_by_name,
                )
            )
        statuses = tuple(statuses)
        progress = calculate_progress(
            definition,
            tuple(entry.identity for entry in statuses),
            obtained,
            frozenset(owned),
        )
        return CollectionAlbum(
            definition,
            statuses,
            progress,
            frozenset(
                threshold
                for claimed_collection, threshold in claimed
                if claimed_collection == str(definition.id)
            ),
        )

    def _resolve_entry(
        self,
        definition: CollectionEntryDefinition,
        obtained,
        owned,
        source_by_identity,
        species_by_name: dict[str, object],
    ) -> CollectionEntryStatus:
        species = species_by_name.get(definition.species_name)
        if species is None:
            raise ValueError(
                f"Collection species {definition.species_name} is unavailable."
            )
        variant = None
        if definition.variant_name is not None:
            variant = next(
                (
                    item
                    for item in species.variants or ()
                    if item.name == definition.variant_name
                ),
                None,
            )
            if variant is None:
                raise ValueError(
                    f"Collection variant {definition.variant_name} is unavailable."
                )
        identity = species.id, variant.id if variant is not None else None
        return CollectionEntryStatus(
            definition,
            species,
            variant,
            identity in obtained,
            identity in owned,
            source_by_identity.get(identity),
            owned.get(identity),
        )

    async def _collection_species_by_name(
        self,
        definitions: tuple[CollectionDefinition, ...],
    ) -> dict[str, object]:
        names = tuple(
            dict.fromkeys(
                entry.species_name
                for definition in definitions
                for entry in definition.entries
            )
        )
        species_by_name = await self._species_repository.find_many_by_names(names)

        for name in names:
            if name not in species_by_name:
                raise ValueError(f"Collection species {name} is unavailable.")

        return species_by_name

    async def _owned_entry_collection_numbers(
        self,
        trainer_id: int,
    ) -> dict[tuple[int, int | None], int | None]:
        creatures = await self._creature_repository.get_by_trainer(trainer_id)
        return {
            (
                creature.species.id,
                creature.current_form.id if creature.current_form is not None else None,
            ): creature.collection_number
            for creature in reversed(creatures)
        }
