import pytest

from application.collection.collection_application_service import (
    CollectionApplicationService,
)
from core.collection.catalog import COLLECTIONS, CollectionId
from core.collection.history import CollectionEntrySource
from core.creature.creature_factory import CreatureFactory
from core.opportunity.opportunity_factory import OpportunityFactory
from core.species.variant import Variant
from test.factories import create_species
from test.fakes.fake_collection_history_repository import (
    FakeCollectionHistoryRepository,
)


class SpeciesRepository:
    def __init__(self, species):
        self.species = {item.name: item for item in species}
        self.find_by_name_calls = []
        self.find_many_by_names_calls = []

    async def find_by_name(self, name):
        self.find_by_name_calls.append(name)
        return self.species.get(name)

    async def find_many_by_names(self, names):
        self.find_many_by_names_calls.append(tuple(names))
        return {name: self.species[name] for name in names if name in self.species}


class CreatureRepository:
    def __init__(self) -> None:
        self.creatures = []

    async def get_by_trainer(self, trainer_id):
        return [
            creature for creature in self.creatures if creature.trainer_id == trainer_id
        ]


def _all_collection_species():
    by_name = {}
    variant_id = 1
    species_id = 1
    for definition in COLLECTIONS:
        for entry in definition.entries:
            item = by_name.get(entry.species_name)
            if item is None:
                item = create_species(
                    id=species_id,
                    name=entry.species_name,
                    variants=[],
                )
                by_name[entry.species_name] = item
                species_id += 1
            if entry.variant_name is not None:
                item.variants.append(Variant(variant_id, entry.variant_name))
                variant_id += 1
    return tuple(by_name.values())


async def _record(
    history,
    creatures,
    trainer_id,
    entry,
    source=CollectionEntrySource.CAPTURE,
    *,
    currently_owned=True,
):
    creature = CreatureFactory.create(
        trainer_id,
        OpportunityFactory.create(entry.species),
    )
    creature.id = entry.species.id * 1000 + (entry.variant.id if entry.variant else 0)
    creature.current_form = entry.variant
    await history.record_creature(creature, source)
    if currently_owned:
        creatures.creatures.append(creature)
    return creature


@pytest.mark.asyncio
async def test_progress_is_historical_and_claims_each_milestone_once():
    trainer_id = 113100351531417600
    history = FakeCollectionHistoryRepository()
    creatures = CreatureRepository()
    service = CollectionApplicationService(
        SpeciesRepository(_all_collection_species()), history, creatures
    )
    album = await service.album(trainer_id, CollectionId.TECHNOLOGY)
    for entry in album.entries[:3]:
        await _record(history, creatures, trainer_id, entry)

    album = await service.album(trainer_id, CollectionId.TECHNOLOGY)
    assert album.progress.collected_count == 3
    assert [item.threshold for item in album.available_milestones] == [3]

    result = await service.claim(trainer_id, CollectionId.TECHNOLOGY, 3)
    assert result.claimed is True
    assert result.milestone.mints == 0
    repeated = await service.claim(trainer_id, CollectionId.TECHNOLOGY, 3)
    assert repeated.claimed is False


@pytest.mark.asyncio
async def test_variant_progress_requires_the_exact_canonical_variant():
    trainer_id = 99
    history = FakeCollectionHistoryRepository()
    creatures = CreatureRepository()
    service = CollectionApplicationService(
        SpeciesRepository(_all_collection_species()), history, creatures
    )
    album = await service.album(trainer_id, CollectionId.ALCREMIE)
    salted_love = next(
        item
        for item in album.entries
        if item.definition.variant_name == "salted-cream-love"
    )
    await _record(
        history,
        creatures,
        trainer_id,
        salted_love,
        CollectionEntrySource.SHOP,
    )

    refreshed = await service.album(trainer_id, CollectionId.ALCREMIE)
    assert refreshed.progress.collected_count == 1
    assert next(
        item
        for item in refreshed.entries
        if item.definition.variant_name == "salted-cream-love"
    ).collected


@pytest.mark.asyncio
async def test_incomplete_milestone_cannot_be_claimed():
    service = CollectionApplicationService(
        SpeciesRepository(_all_collection_species()),
        FakeCollectionHistoryRepository(),
        CreatureRepository(),
    )
    with pytest.raises(ValueError, match="not complete"):
        await service.claim(7, CollectionId.FOSSIL_RESTORATION, 5)


@pytest.mark.asyncio
async def test_trade_history_requires_current_ownership_for_claim():
    trainer_id = 9
    history = FakeCollectionHistoryRepository()
    creatures = CreatureRepository()
    service = CollectionApplicationService(
        SpeciesRepository(_all_collection_species()), history, creatures
    )
    album = await service.album(trainer_id, CollectionId.TECHNOLOGY)
    received = [
        await _record(
            history,
            creatures,
            trainer_id,
            entry,
            CollectionEntrySource.TRADE,
        )
        for entry in album.entries[:3]
    ]

    creatures.creatures.remove(received[-1])
    refreshed = await service.album(trainer_id, CollectionId.TECHNOLOGY)
    assert refreshed.progress.historical_count == 3
    assert refreshed.progress.owned_count == 2
    assert refreshed.entries[2].historically_obtained is True
    assert refreshed.entries[2].currently_owned is False
    with pytest.raises(ValueError, match="current collection"):
        await service.claim(trainer_id, CollectionId.TECHNOLOGY, 3)

    creatures.creatures.append(received[-1])
    result = await service.claim(trainer_id, CollectionId.TECHNOLOGY, 3)
    assert result.claimed is True
    creatures.creatures.clear()
    after_return = await service.album(trainer_id, CollectionId.TECHNOLOGY)
    assert after_return.progress.historical_count == 3


@pytest.mark.asyncio
async def test_duplicate_current_creatures_do_not_increase_owned_collection_progress():
    trainer_id = 10
    history = FakeCollectionHistoryRepository()
    creatures = CreatureRepository()
    service = CollectionApplicationService(
        SpeciesRepository(_all_collection_species()), history, creatures
    )
    entry = (await service.album(trainer_id, CollectionId.TECHNOLOGY)).entries[0]
    first = await _record(history, creatures, trainer_id, entry)
    creatures.creatures.append(first)

    album = await service.album(trainer_id, CollectionId.TECHNOLOGY)
    assert album.progress.historical_count == 1
    assert album.progress.owned_count == 1


@pytest.mark.asyncio
async def test_backfilled_owned_technology_entry_is_also_historical():
    trainer_id = 113100351531417600
    history = FakeCollectionHistoryRepository()
    creatures = CreatureRepository()
    service = CollectionApplicationService(
        SpeciesRepository(_all_collection_species()), history, creatures
    )
    porygon = (await service.album(trainer_id, CollectionId.TECHNOLOGY)).entries[0]

    await _record(
        history,
        creatures,
        trainer_id,
        porygon,
        CollectionEntrySource.BACKFILL,
    )

    album = await service.album(trainer_id, CollectionId.TECHNOLOGY)
    assert album.progress.historical_count == 1
    assert album.progress.owned_count == 1


@pytest.mark.asyncio
async def test_shop_porygon_is_owned_and_historical_immediately():
    trainer_id = 113100351531417600
    history = FakeCollectionHistoryRepository()
    creatures = CreatureRepository()
    service = CollectionApplicationService(
        SpeciesRepository(_all_collection_species()), history, creatures
    )
    porygon = (await service.album(trainer_id, CollectionId.TECHNOLOGY)).entries[0]

    await _record(history, creatures, trainer_id, porygon, CollectionEntrySource.SHOP)

    album = await service.album(trainer_id, CollectionId.TECHNOLOGY)
    assert album.progress.historical_count == 1
    assert album.progress.owned_count == 1


@pytest.mark.asyncio
async def test_albums_load_collection_species_once_without_per_entry_queries():
    species_repository = SpeciesRepository(_all_collection_species())
    service = CollectionApplicationService(
        species_repository,
        FakeCollectionHistoryRepository(),
        CreatureRepository(),
    )

    albums = await service.albums(7)

    expected_names = tuple(
        dict.fromkeys(
            entry.species_name
            for definition in COLLECTIONS
            for entry in definition.entries
        )
    )
    assert species_repository.find_many_by_names_calls == [expected_names]
    assert species_repository.find_by_name_calls == []
    assert [album.definition.id for album in albums] == [
        definition.id for definition in COLLECTIONS
    ]
    assert sum(len(album.entries) for album in albums) == 105
    assert all(
        entry.species.name == entry.definition.species_name
        and (
            entry.variant is None or entry.variant.name == entry.definition.variant_name
        )
        for album in albums
        for entry in album.entries
    )


@pytest.mark.asyncio
async def test_albums_report_a_missing_canonical_collection_species():
    species = list(_all_collection_species())
    species = [item for item in species if item.name != "porygon"]
    service = CollectionApplicationService(
        SpeciesRepository(species),
        FakeCollectionHistoryRepository(),
        CreatureRepository(),
    )

    with pytest.raises(ValueError, match="Collection species porygon is unavailable"):
        await service.albums(7)


@pytest.mark.asyncio
async def test_claim_from_an_obsolete_snapshot_revalidates_current_ownership():
    trainer_id = 113100351531417600
    history = FakeCollectionHistoryRepository()
    creatures = CreatureRepository()
    service = CollectionApplicationService(
        SpeciesRepository(_all_collection_species()), history, creatures
    )
    initial = await service.album(trainer_id, CollectionId.TECHNOLOGY)
    owned = [
        await _record(history, creatures, trainer_id, entry)
        for entry in initial.entries[:3]
    ]
    snapshot = await service.album(trainer_id, CollectionId.TECHNOLOGY)
    assert [item.threshold for item in snapshot.available_milestones] == [3]

    creatures.creatures.remove(owned[-1])

    with pytest.raises(ValueError, match="current collection"):
        await service.claim(trainer_id, CollectionId.TECHNOLOGY, 3)
    assert history.claim_calls == []
