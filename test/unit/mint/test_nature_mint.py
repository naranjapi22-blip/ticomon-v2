import pytest

from application.mint.nature_mint_application_service import (
    NatureMintApplicationService,
)
from core.creature.creature_mapper import CreatureMapper
from core.creature.nature import Nature
from core.creature.stat import Stat
from core.mint.nature_mint_inventory import NatureMintInventory
from test.builders.creature_builder import CreatureBuilder
from test.fakes.fake_creature_repository import FakeCreatureRepository


def test_nature_mint_inventory_never_goes_negative():
    inventory = NatureMintInventory(1)
    inventory.consume_one()
    assert inventory.amount == 0
    with pytest.raises(ValueError):
        inventory.consume_one()


def test_nature_effect_resolves_only_official_natures():
    assert Nature.from_effect(Stat.ATTACK, Stat.SP_ATTACK) == Nature("adamant")
    with pytest.raises(ValueError):
        Nature.from_effect(Stat.HP, Stat.ATTACK)
    with pytest.raises(ValueError):
        Nature.from_effect(Stat.ATTACK, Stat.ATTACK)


def test_creature_uses_original_until_a_mint_exists():
    creature = CreatureBuilder().build()
    assert creature.effective_nature == creature.nature
    creature.minted_nature = Nature("jolly")
    assert creature.effective_nature == Nature("jolly")


def test_mapper_round_trips_null_and_minted_nature():
    creature = CreatureBuilder().build()
    row = {
        "id": 1,
        "collection_number": 1,
        "trainer_id": 1,
        "original_trainer_id": 1,
        "species_id": creature.species.id,
        "hp_iv": creature.ivs.hp,
        "attack_iv": creature.ivs.attack,
        "defense_iv": creature.ivs.defense,
        "special_attack_iv": creature.ivs.special_attack,
        "special_defense_iv": creature.ivs.special_defense,
        "speed_iv": creature.ivs.speed,
        "size": creature.size.value,
        "nature": creature.nature.name,
        "minted_nature": None,
        "is_shiny": creature.is_shiny,
        "variant_id": None,
        "variant_name": None,
    }
    restored = CreatureMapper.from_row(row, creature.species)
    assert restored.minted_nature is None
    restored.minted_nature = Nature("adamant")
    assert CreatureMapper.to_row(restored)[13] == "adamant"


class _FakeMintRepository:
    def __init__(self, creature, amount=1):
        self.creature = creature
        self.amount = amount

    async def get(self, trainer_id):
        return NatureMintInventory(self.amount)

    async def apply(self, trainer_id, collection_number, minted_nature):
        if self.amount <= 0:
            raise ValueError("Insufficient Nature Mints.")
        if (
            minted_nature is not None
            and minted_nature == self.creature.effective_nature
        ):
            raise ValueError("Creature already has that nature effect.")
        self.amount -= 1
        self.creature.minted_nature = minted_nature
        return self.creature, self.amount


@pytest.mark.asyncio
async def test_application_consumes_one_mint_and_can_restore_original():
    creature = CreatureBuilder().with_id(7).with_collection_number(7).build()
    repository = FakeCreatureRepository(creature)
    mint_repository = _FakeMintRepository(creature, amount=2)
    service = NatureMintApplicationService(repository, mint_repository)

    result = await service.apply(1, 7, Stat.ATTACK, Stat.SP_ATTACK)
    assert result.creature.minted_nature == Nature("adamant")
    assert result.remaining_mints == 1

    result = await service.apply(1, 7, None, None)
    assert result.creature.minted_nature is None
    assert result.remaining_mints == 0
