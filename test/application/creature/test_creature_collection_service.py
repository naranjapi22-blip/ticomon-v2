import pytest

from application.creature.creature_collection_service import (
    CreatureCollectionService,
    TopMetric,
)
from core.creature.creature import Creature
from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.creature.size import Size
from core.creature.stat import Stat
from test.builders.species_builder import SpeciesBuilder
from test.fakes.fake_creature_repository import FakeCreatureRepository
from test.fakes.fake_species_repository import FakeSpeciesRepository


def _creature(
    *,
    species,
    trainer_id: int,
    collection_number: int,
    ivs: tuple[int, int, int, int, int, int],
    shiny: bool = False,
    nature: str = "hardy",
    minted_nature: str | None = None,
    creature_id: int,
) -> Creature:
    return Creature(
        species=species,
        trainer_id=trainer_id,
        ivs=IVs(
            hp=ivs[0],
            attack=ivs[1],
            defense=ivs[2],
            special_attack=ivs[3],
            special_defense=ivs[4],
            speed=ivs[5],
        ),
        size=Size(1.0),
        nature=Nature(nature),
        minted_nature=Nature(minted_nature) if minted_nature else None,
        is_shiny=shiny,
        current_form=None,
        id=creature_id,
        collection_number=collection_number,
    )


def _service(*creatures: Creature) -> CreatureCollectionService:
    fire = (
        SpeciesBuilder()
        .with_id(1)
        .with_name("Charmander")
        .with_types(
            ["fire"],
        )
        .build()
    )

    water = (
        SpeciesBuilder()
        .with_id(2)
        .with_name("Squirtle")
        .with_types(
            ["water"],
        )
        .build()
    )
    dual = (
        SpeciesBuilder()
        .with_id(3)
        .with_name("Pidgey")
        .with_types(
            ["fire", "flying"],
        )
        .build()
    )

    species_repository = FakeSpeciesRepository(
        fire,
        water,
        dual,
    )

    return CreatureCollectionService(
        creature_repository=FakeCreatureRepository(*creatures),
        species_repository=species_repository,
    )


class _FixedStatCalculator:
    def __init__(self, values: dict[int, dict[Stat, int]]) -> None:
        self.values = values

    def calculate(self, creature: Creature, stat: Stat) -> int:
        return self.values[creature.id][stat]


@pytest.mark.asyncio
async def test_top_collection_orders_by_iv_descending() -> None:
    fire = (
        SpeciesBuilder()
        .with_id(1)
        .with_name("Charmander")
        .with_types(
            ["fire"],
        )
        .build()
    )
    water = (
        SpeciesBuilder()
        .with_id(2)
        .with_name("Squirtle")
        .with_types(
            ["water"],
        )
        .build()
    )
    dual = (
        SpeciesBuilder()
        .with_id(3)
        .with_name("Pidgey")
        .with_types(
            ["fire", "flying"],
        )
        .build()
    )

    creatures = [
        _creature(
            species=fire,
            trainer_id=1,
            collection_number=11,
            ivs=(31, 31, 31, 31, 31, 31),
            creature_id=101,
        ),
        _creature(
            species=water,
            trainer_id=1,
            collection_number=12,
            ivs=(25, 25, 25, 25, 25, 25),
            creature_id=102,
        ),
        _creature(
            species=dual,
            trainer_id=1,
            collection_number=13,
            ivs=(29, 29, 29, 29, 29, 29),
            creature_id=103,
        ),
    ]

    service = CreatureCollectionService(
        creature_repository=FakeCreatureRepository(*creatures),
        species_repository=FakeSpeciesRepository(
            fire,
            water,
            dual,
        ),
    )

    result = await service.get_top_collection(trainer_id=1)

    assert [creature.id for creature in result] == [101, 103, 102]


@pytest.mark.asyncio
async def test_top_rankings_use_level_50_nature_aware_stats() -> None:
    species = (
        SpeciesBuilder().with_id(1).with_name("Testmon").with_types(["fire"]).build()
    )
    service = _service(
        _creature(
            species=species,
            trainer_id=1,
            collection_number=1,
            ivs=(0, 31, 0, 0, 0, 0),
            creature_id=101,
        ),
        _creature(
            species=species,
            trainer_id=1,
            collection_number=2,
            ivs=(0, 0, 0, 0, 0, 31),
            creature_id=102,
        ),
    )

    rankings = await service.get_top_rankings(
        trainer_id=1,
        metric=TopMetric.SPEED,
        pokemon_type="fire",
    )

    assert [item.creature.id for item in rankings] == [102, 101]
    assert rankings[0].stats["Speed"] == 65
    assert rankings[0].score == rankings[0].stats["Speed"]


@pytest.mark.asyncio
async def test_top_rankings_use_minted_nature_over_original_nature() -> None:
    species = SpeciesBuilder().with_id(1).build()
    service = _service(
        _creature(
            species=species,
            trainer_id=1,
            collection_number=1,
            ivs=(0, 0, 0, 0, 0, 0),
            nature="adamant",
            minted_nature="modest",
            creature_id=101,
        ),
    )

    rankings = await service.get_top_rankings(
        trainer_id=1,
        metric=TopMetric.SPECIAL_ATTACK,
    )

    assert rankings[0].stats["Sp. Atk"] == 77


@pytest.mark.asyncio
async def test_top_rankings_apply_metric_scores_and_deterministic_tiebreakers() -> None:
    species = SpeciesBuilder().with_id(1).with_name("Testmon").build()
    creatures = [
        _creature(
            species=species,
            trainer_id=1,
            collection_number=2,
            ivs=(0, 0, 0, 0, 0, 0),
            creature_id=101,
        ),
        _creature(
            species=species,
            trainer_id=1,
            collection_number=1,
            ivs=(0, 0, 0, 0, 0, 0),
            creature_id=102,
        ),
        _creature(
            species=species,
            trainer_id=1,
            collection_number=3,
            ivs=(0, 0, 0, 0, 0, 0),
            creature_id=103,
        ),
    ]
    values = {
        101: {
            Stat.HP: 100,
            Stat.ATTACK: 200,
            Stat.DEFENSE: 80,
            Stat.SP_ATTACK: 50,
            Stat.SP_DEFENSE: 70,
            Stat.SPEED: 100,
        },
        102: {
            Stat.HP: 120,
            Stat.ATTACK: 200,
            Stat.DEFENSE: 80,
            Stat.SP_ATTACK: 60,
            Stat.SP_DEFENSE: 70,
            Stat.SPEED: 100,
        },
        103: {
            Stat.HP: 120,
            Stat.ATTACK: 180,
            Stat.DEFENSE: 100,
            Stat.SP_ATTACK: 90,
            Stat.SP_DEFENSE: 90,
            Stat.SPEED: 110,
        },
    }
    service = CreatureCollectionService(
        creature_repository=FakeCreatureRepository(*creatures),
        species_repository=FakeSpeciesRepository(species),
        stat_calculator=_FixedStatCalculator(values),
    )

    physical_attack = await service.get_top_rankings(
        trainer_id=1,
        metric=TopMetric.PHYSICAL_ATTACK,
    )
    physical_bulk = await service.get_top_rankings(
        trainer_id=1,
        metric=TopMetric.PHYSICAL_DEFENSE,
    )
    special_bulk = await service.get_top_rankings(
        trainer_id=1,
        metric=TopMetric.SPECIAL_DEFENSE,
    )
    speed = await service.get_top_rankings(
        trainer_id=1,
        metric=TopMetric.SPEED,
    )

    assert [item.creature.id for item in physical_attack] == [102, 101, 103]
    assert [item.creature.id for item in physical_bulk] == [103, 102, 101]
    assert [item.creature.id for item in special_bulk] == [103, 102, 101]
    assert [item.creature.id for item in speed] == [103, 102, 101]
    assert physical_bulk[0].score == 220
    assert special_bulk[0].score == 210
    assert speed[0].score == 110


@pytest.mark.asyncio
async def test_top_rankings_filter_primary_and_secondary_types() -> None:
    fire = SpeciesBuilder().with_id(1).with_types(["fire"]).build()
    dual = SpeciesBuilder().with_id(2).with_types(["water", "flying"]).build()
    service = _service(
        _creature(
            species=fire,
            trainer_id=1,
            collection_number=1,
            ivs=(0, 0, 0, 0, 0, 0),
            creature_id=101,
        ),
        _creature(
            species=dual,
            trainer_id=1,
            collection_number=2,
            ivs=(0, 0, 0, 0, 0, 0),
            creature_id=102,
        ),
    )

    rankings = await service.get_top_rankings(
        trainer_id=1,
        pokemon_type="FLYING",
    )

    assert [item.creature.id for item in rankings] == [102]


@pytest.mark.asyncio
async def test_rank_snapshot_reuses_loaded_creatures_without_repository_access() -> (
    None
):
    species = SpeciesBuilder().with_id(1).build()
    creature = _creature(
        species=species,
        trainer_id=1,
        collection_number=1,
        ivs=(31, 31, 31, 31, 31, 31),
        creature_id=101,
    )
    repository = FakeCreatureRepository(creature)
    service = CreatureCollectionService(
        creature_repository=repository,
        species_repository=FakeSpeciesRepository(species),
    )

    snapshot = await service.get_top_rankings(trainer_id=1)
    reranked = service.rank_snapshot(
        snapshot,
        metric=TopMetric.SPEED,
        pokemon_type=None,
    )

    assert [item.creature.id for item in reranked] == [101]


@pytest.mark.asyncio
async def test_top_collection_uses_collection_number_descending_as_tiebreaker() -> None:
    fire = (
        SpeciesBuilder()
        .with_id(1)
        .with_name("Charmander")
        .with_types(
            ["fire"],
        )
        .build()
    )
    dual = (
        SpeciesBuilder()
        .with_id(3)
        .with_name("Pidgey")
        .with_types(
            ["fire", "flying"],
        )
        .build()
    )

    service = _service(
        _creature(
            species=fire,
            trainer_id=1,
            collection_number=11,
            ivs=(30, 30, 30, 30, 30, 30),
            creature_id=101,
        ),
        _creature(
            species=dual,
            trainer_id=1,
            collection_number=13,
            ivs=(30, 30, 30, 30, 30, 30),
            creature_id=103,
        ),
        _creature(
            species=fire,
            trainer_id=1,
            collection_number=12,
            ivs=(30, 30, 30, 30, 30, 30),
            creature_id=102,
        ),
    )

    result = await service.get_top_collection(trainer_id=1)

    assert [creature.collection_number for creature in result] == [13, 12, 11]


@pytest.mark.asyncio
async def test_top_collection_filters_monotype_and_dual_type() -> None:
    fire = (
        SpeciesBuilder()
        .with_id(1)
        .with_name("Charmander")
        .with_types(
            ["fire"],
        )
        .build()
    )
    dual = (
        SpeciesBuilder()
        .with_id(3)
        .with_name("Pidgey")
        .with_types(
            ["fire", "flying"],
        )
        .build()
    )
    water = (
        SpeciesBuilder()
        .with_id(2)
        .with_name("Squirtle")
        .with_types(
            ["water"],
        )
        .build()
    )

    service = _service(
        _creature(
            species=fire,
            trainer_id=1,
            collection_number=11,
            ivs=(31, 31, 31, 31, 31, 31),
            creature_id=101,
        ),
        _creature(
            species=dual,
            trainer_id=1,
            collection_number=12,
            ivs=(29, 29, 29, 29, 29, 29),
            creature_id=103,
        ),
        _creature(
            species=water,
            trainer_id=1,
            collection_number=13,
            ivs=(25, 25, 25, 25, 25, 25),
            creature_id=102,
        ),
    )

    result = await service.get_top_collection(
        trainer_id=1,
        pokemon_type="FiRe",
    )

    assert [creature.id for creature in result] == [101, 103]


@pytest.mark.asyncio
async def test_inventory_collection_orders_by_collection_number_descending() -> None:
    fire = (
        SpeciesBuilder()
        .with_id(1)
        .with_name("Charmander")
        .with_types(
            ["fire"],
        )
        .build()
    )
    water = (
        SpeciesBuilder()
        .with_id(2)
        .with_name("Squirtle")
        .with_types(
            ["water"],
        )
        .build()
    )
    dual = (
        SpeciesBuilder()
        .with_id(3)
        .with_name("Pidgey")
        .with_types(
            ["normal", "flying"],
        )
        .build()
    )

    service = _service(
        _creature(
            species=fire,
            trainer_id=1,
            collection_number=4,
            ivs=(31, 31, 31, 31, 31, 31),
            creature_id=101,
        ),
        _creature(
            species=water,
            trainer_id=1,
            collection_number=7,
            ivs=(25, 25, 25, 25, 25, 25),
            creature_id=102,
        ),
        _creature(
            species=dual,
            trainer_id=1,
            collection_number=6,
            ivs=(29, 29, 29, 29, 29, 29),
            creature_id=103,
        ),
    )

    result = await service.get_recent_collection(trainer_id=1)

    assert [creature.collection_number for creature in result] == [7, 6, 4]


@pytest.mark.asyncio
async def test_inventory_collection_filters_by_type() -> None:
    fire = (
        SpeciesBuilder()
        .with_id(1)
        .with_name("Charmander")
        .with_types(
            ["fire"],
        )
        .build()
    )
    water = (
        SpeciesBuilder()
        .with_id(2)
        .with_name("Squirtle")
        .with_types(
            ["water"],
        )
        .build()
    )
    dual = (
        SpeciesBuilder()
        .with_id(3)
        .with_name("Pidgey")
        .with_types(
            ["water", "flying"],
        )
        .build()
    )

    service = _service(
        _creature(
            species=fire,
            trainer_id=1,
            collection_number=4,
            ivs=(31, 31, 31, 31, 31, 31),
            creature_id=101,
        ),
        _creature(
            species=water,
            trainer_id=1,
            collection_number=7,
            ivs=(25, 25, 25, 25, 25, 25),
            creature_id=102,
        ),
        _creature(
            species=dual,
            trainer_id=1,
            collection_number=6,
            ivs=(29, 29, 29, 29, 29, 29),
            creature_id=103,
        ),
    )

    result = await service.get_recent_collection(
        trainer_id=1,
        pokemon_type="WATER",
    )

    assert [creature.collection_number for creature in result] == [7, 6]


@pytest.mark.asyncio
async def test_inventory_collection_filters_shiny_only() -> None:
    fire = (
        SpeciesBuilder()
        .with_id(1)
        .with_name("Charmander")
        .with_types(
            ["fire"],
        )
        .build()
    )
    water = (
        SpeciesBuilder()
        .with_id(2)
        .with_name("Squirtle")
        .with_types(
            ["water"],
        )
        .build()
    )

    service = _service(
        _creature(
            species=fire,
            trainer_id=1,
            collection_number=4,
            ivs=(31, 31, 31, 31, 31, 31),
            shiny=True,
            creature_id=101,
        ),
        _creature(
            species=water,
            trainer_id=1,
            collection_number=7,
            ivs=(25, 25, 25, 25, 25, 25),
            shiny=False,
            creature_id=102,
        ),
    )

    result = await service.get_recent_collection(
        trainer_id=1,
        shiny_only=True,
    )

    assert [creature.collection_number for creature in result] == [4]


@pytest.mark.asyncio
async def test_collection_service_rejects_unknown_type() -> None:
    service = _service()

    with pytest.raises(ValueError, match="Unknown Pokémon type: abc"):
        await service.get_top_collection(
            trainer_id=1,
            pokemon_type="abc",
        )
