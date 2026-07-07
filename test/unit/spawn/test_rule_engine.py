from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.region import Region
from core.spawn.rule import Rule
from core.spawn.rule_engine import RuleEngine
from core.spawn.world import World
from test.factories import create_species


class AllowAllRule(Rule):
    def allows(
        self,
        species,
        context,
        profile,
    ) -> bool:
        return True


class RejectAllRule(Rule):
    def allows(
        self,
        species,
        context,
        profile,
    ) -> bool:
        return False


class EvenIdRule(Rule):
    def allows(
        self,
        species,
        context,
        profile,
    ) -> bool:
        return species.id % 2 == 0


def create_context():
    return SpawnContext(
        world=World.MAIN,
        region=Region.KANTO,
    )


def create_profile():
    return SpawnProfile(
        opportunity_count=3,
    )


def test_returns_same_species_when_no_rules():

    engine = RuleEngine()

    species = (
        create_species(id=1),
        create_species(id=2, name="Charmander"),
        create_species(id=3, name="Bulbasaur"),
    )

    result = engine.apply(
        species_pool=species,
        rules=(),
        context=create_context(),
        profile=create_profile(),
    )

    assert result == species


def test_allow_all_rule_returns_every_species():

    engine = RuleEngine()

    species = (
        create_species(id=1),
        create_species(id=2, name="Charmander"),
    )

    result = engine.apply(
        species_pool=species,
        rules=(AllowAllRule(),),
        context=create_context(),
        profile=create_profile(),
    )

    assert result == species


def test_reject_all_rule_returns_empty_tuple():

    engine = RuleEngine()

    species = (
        create_species(id=1),
        create_species(id=2),
    )

    result = engine.apply(
        species_pool=species,
        rules=(RejectAllRule(),),
        context=create_context(),
        profile=create_profile(),
    )

    assert result == ()


def test_filters_species_using_rules():

    engine = RuleEngine()

    species = (
        create_species(id=1),
        create_species(id=2, name="Charmander"),
        create_species(id=3, name="Bulbasaur"),
        create_species(id=4, name="Squirtle"),
    )

    result = engine.apply(
        species_pool=species,
        rules=(EvenIdRule(),),
        context=create_context(),
        profile=create_profile(),
    )

    ids = [pokemon.id for pokemon in result]

    assert ids == [2, 4]


def test_every_rule_must_allow_species():

    engine = RuleEngine()

    species = (
        create_species(id=1),
        create_species(id=2),
    )

    result = engine.apply(
        species_pool=species,
        rules=(
            AllowAllRule(),
            RejectAllRule(),
        ),
        context=create_context(),
        profile=create_profile(),
    )

    assert result == ()
