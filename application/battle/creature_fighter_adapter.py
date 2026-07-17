from core.battle.engine.battle_fighter import BattleFighter
from core.battle.ports.damage_calculator import LearnsetProvider
from core.battle.rules.move_policy import pick_automatic_move
from core.battle.species_id import to_species_showdown_id
from core.creature.creature import Creature
from core.creature.stat import Stat
from core.stats.stat_calculator import StatCalculator


class CreatureFighterAdapter:
    """Maps TicoMon creatures to reusable battle fighters."""

    def __init__(
        self,
        stat_calculator: StatCalculator,
        learnset_provider: LearnsetProvider,
    ) -> None:
        self._stat_calculator = stat_calculator
        self._learnset_provider = learnset_provider

    def build_many(
        self,
        creatures: list[Creature],
    ) -> tuple[BattleFighter, ...]:
        return tuple(self.build(creature) for creature in creatures)

    def build(self, creature: Creature) -> BattleFighter:
        if creature.id is None:
            raise ValueError("Creature must have an id for battle.")

        species = creature.species
        species_showdown_id = to_species_showdown_id(species.name)
        learnset = self._learnset_provider.get_learnset(species_showdown_id)

        attack = self._stat_calculator.calculate(creature, Stat.ATTACK)
        special_attack = self._stat_calculator.calculate(creature, Stat.SP_ATTACK)

        move_id, move_name = pick_automatic_move(
            species_showdown_id,
            attack=attack,
            special_attack=special_attack,
            types=tuple(species.types),
            learnset=learnset,
        )

        display_name = species.name.title()
        if creature.is_shiny:
            display_name = f"✨ {display_name}"

        return BattleFighter(
            creature_id=creature.id,
            display_name=display_name,
            species_showdown_id=species_showdown_id,
            nature_showdown_id=creature.effective_nature.name,
            types=tuple(species.types),
            hp_max=self._stat_calculator.calculate(creature, Stat.HP),
            attack=attack,
            special_attack=special_attack,
            defense=self._stat_calculator.calculate(creature, Stat.DEFENSE),
            special_defense=self._stat_calculator.calculate(
                creature,
                Stat.SP_DEFENSE,
            ),
            speed=self._stat_calculator.calculate(creature, Stat.SPEED),
            move_id=move_id,
            move_display_name=move_name,
            pokeapi_id=species.pokeapi_id,
            is_shiny=creature.is_shiny,
        )
