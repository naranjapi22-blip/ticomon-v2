import pytest

from core.creature.ability import Ability, AbilityAssignmentPolicy
from core.creature.move import validate_moves
from core.pvp.session import PvpPhase, PvpSessionRegistry


class _Catalog:
    def abilities_for(self, species_id):
        return (Ability("static", "Static"), Ability("lightningrod", "Lightning Rod"))


def test_ability_assignment_is_stable_without_random_source():
    policy = AbilityAssignmentPolicy(_Catalog())
    assert policy.assign_for_species(
        25, seed="creature-1"
    ) == policy.assign_for_species(25, seed="creature-1")


def test_moves_are_limited_and_unique():
    assert validate_moves(["Thunderbolt", "quick attack"]) == (
        "thunderbolt",
        "quick-attack",
    )
    with pytest.raises(ValueError):
        validate_moves(["a", "b", "c", "d", "e"])
    with pytest.raises(ValueError):
        validate_moves(["a", "a"])


def test_pvp_registry_releases_both_players():
    registry = PvpSessionRegistry()
    session = registry.create(1, 2)
    session.select_team(1, [10, 11, 12])
    session.select_team(2, [20, 21, 22])
    assert session.phase is PvpPhase.WAITING_FOR_ACTIONS
    registry.remove(session.id)
    registry.create(1, 2)
