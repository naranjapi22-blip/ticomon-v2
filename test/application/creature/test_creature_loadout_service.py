from types import SimpleNamespace

import pytest

from application.creature.creature_loadout_service import CreatureLoadoutService
from core.creature.move import CreatureMove


class Repository:
    def __init__(self, creature, legal_moves):
        self.creature = creature
        self.legal_moves = legal_moves
        self.updated = []

    async def get_by_collection_number(self, trainer_id, collection_number):
        if (trainer_id, collection_number) != (
            self.creature.trainer_id,
            self.creature.collection_number,
        ):
            raise ValueError("not found")
        return self.creature

    async def get_legal_moves(self, species_id):
        return self.legal_moves

    async def update_moves(self, **kwargs):
        self.updated.append(kwargs)
        self.creature.moves = kwargs["moves"]
        return self.creature


class Catalog:
    def __init__(self, moves):
        self.moves = moves

    def moves_for(self, species):
        return self.moves

    def abilities_for(self, species):
        return (SimpleNamespace(id="static", display_name="Static"),)


def move(move_id, *, power=40, accuracy=100, pp=35):
    return CreatureMove(
        move_id, move_id.title(), "normal", "Physical", power, accuracy, pp
    )


@pytest.fixture
def service():
    legal = (move("tackle"), move("growl", power=None, accuracy=None, pp=40))
    creature = SimpleNamespace(
        trainer_id=7,
        collection_number=2,
        species=SimpleNamespace(id=25, name="Pikachu"),
        ability_id="static",
        moves=("tackle",),
    )
    repository = Repository(creature, legal)
    return CreatureLoadoutService(repository, Catalog(legal)), repository


@pytest.mark.asyncio
async def test_loadout_contains_ability_and_move_metadata(service):
    application, _ = service
    loadout = await application.get_loadout(7, 2)
    assert loadout.ability.display_name == "Static"
    assert loadout.moves[0].pp == 35
    assert loadout.legal_moves[1].base_power is None
    assert loadout.legal_moves[1].accuracy is None


@pytest.mark.asyncio
async def test_update_rejects_illegal_and_duplicate_moves(service):
    application, repository = service
    with pytest.raises(ValueError, match="not legal"):
        await application.update_moves(7, 2, ("teleport",))
    with pytest.raises(ValueError, match="duplicate"):
        await application.update_moves(7, 2, ("tackle", "tackle"))
    assert repository.updated == []


@pytest.mark.asyncio
async def test_update_accepts_one_to_four_and_preserves_ability(service):
    application, repository = service
    result = await application.update_moves(7, 2, ("growl",))
    assert result.creature.moves == ("growl",)
    assert repository.updated[0]["ability_id"] == "static"
