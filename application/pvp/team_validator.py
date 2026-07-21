from __future__ import annotations

from collections.abc import Iterable

from core.creature.creature import Creature
from infrastructure.battle.poke_env.loadout_catalog import PokeEnvLoadoutCatalog
from infrastructure.battle.poke_env.pvp_set_adapter import PvpSetAdapter


class PvpTeamValidator:
    def __init__(
        self,
        set_adapter: PvpSetAdapter | None = None,
        catalog: PokeEnvLoadoutCatalog | None = None,
    ) -> None:
        self._set_adapter = set_adapter or PvpSetAdapter()
        self._catalog = catalog or PokeEnvLoadoutCatalog()

    def validate(self, creatures: Iterable[Creature]) -> tuple[Creature, ...]:
        team = tuple(creatures)
        if len(team) != 3:
            raise ValueError("A PvP team must contain exactly three creatures.")
        if len({creature.id for creature in team}) != 3:
            raise ValueError("A PvP team cannot contain duplicate creatures.")
        if len({creature.species.id for creature in team}) != 3:
            raise ValueError("A PvP team cannot contain duplicate species.")

        for creature in team:
            self.validate_creature(creature)
        return team

    def validate_creature(self, creature: Creature) -> Creature:
        if not creature.ability_id:
            raise ValueError(f"{creature.species.name} has no valid persisted ability.")
        valid_abilities = {
            ability.id for ability in self._catalog.abilities_for(creature.species)
        }
        if creature.ability_id not in valid_abilities:
            raise ValueError(f"{creature.species.name} has an invalid ability.")
        legal_moves = {move.id for move in self._catalog.moves_for(creature.species)}
        if not creature.moves or len(creature.moves) > 4:
            raise ValueError(
                f"{creature.species.name} must have one to four equipped moves."
            )
        if any(move not in legal_moves for move in creature.moves):
            raise ValueError(f"{creature.species.name} has an illegal move.")
        self._set_adapter.to_showdown_set(creature)
        return creature
