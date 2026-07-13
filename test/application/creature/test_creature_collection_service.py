import pytest

from application.creature.creature_collection_service import (
    CreatureCollectionService,
)
from core.creature.creature import Creature
from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.creature.size import Size
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
        nature=Nature("hardy"),
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
