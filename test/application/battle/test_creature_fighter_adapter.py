import pytest

from application.battle.creature_fighter_adapter import CreatureFighterAdapter
from core.creature.stat import Stat
from core.stats.stat_calculator import StatCalculator
from test.builders.creature_builder import CreatureBuilder
from test.builders.species_builder import SpeciesBuilder
from test.fakes.fake_learnset_provider import FakeLearnsetProvider


@pytest.fixture
def adapter():
    return CreatureFighterAdapter(
        stat_calculator=StatCalculator(),
        learnset_provider=FakeLearnsetProvider(),
    )


def test_creature_fighter_adapter_uses_species_and_stat_calculator(adapter):
    species = SpeciesBuilder().with_name("Charmander").with_types(["fire"]).build()
    creature = (
        CreatureBuilder().with_id(10).with_species(species).with_trainer_id(1).build()
    )

    fighter = adapter.build(creature)
    calculator = StatCalculator()

    assert fighter.types == ("fire",)
    assert fighter.pokeapi_id == species.pokeapi_id
    assert fighter.hp_max == calculator.calculate(creature, Stat.HP)
    assert fighter.attack == calculator.calculate(creature, Stat.ATTACK)
    assert fighter.speed == calculator.calculate(creature, Stat.SPEED)
    assert fighter.move_id in {"tackle", "ember"}
