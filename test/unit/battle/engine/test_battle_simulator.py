from core.battle.engine.battle_fighter import BattleFighter
from core.battle.engine.battle_simulator import BattleSimulator
from core.battle.ports.damage_calculator import DamageCalculator, DamageResult


class FixedDamageCalculator(DamageCalculator):
    def __init__(self, damage: int = 999) -> None:
        self._damage = damage

    def calculate(
        self,
        attacker: BattleFighter,
        defender: BattleFighter,
        *,
        random_source,
    ) -> DamageResult:
        return DamageResult(
            damage=self._damage,
            hit=True,
            critical=False,
            effectiveness_label="",
            message=f"{attacker.display_name} hits for {self._damage}.",
        )


def build_fighter(
    *,
    name: str,
    speed: int,
    hp: int = 100,
    creature_id: int = 1,
) -> BattleFighter:
    return BattleFighter(
        creature_id=creature_id,
        display_name=name,
        species_showdown_id="pikachu",
        nature_showdown_id="hardy",
        types=("electric",),
        hp_max=hp,
        attack=50,
        special_attack=50,
        defense=50,
        special_defense=50,
        speed=speed,
        move_id="tackle",
        move_display_name="Tackle",
        pokeapi_id=25,
        is_shiny=False,
    )


def test_faster_fighter_wins_when_dealing_lethal_damage():
    simulator = BattleSimulator(FixedDamageCalculator(damage=999))

    team_a = (build_fighter(name="Fast", speed=100, creature_id=1),)
    team_b = (build_fighter(name="Slow", speed=10, creature_id=2),)

    result = simulator.run(
        team_a,
        team_b,
        side_a_name="Player A",
        side_b_name="Player B",
    )

    assert result.winner_side_name == "Player A"


def test_battle_emits_start_and_victory_steps():
    simulator = BattleSimulator(FixedDamageCalculator(damage=999))

    team_a = (build_fighter(name="A1", speed=90, creature_id=1),)
    team_b = (build_fighter(name="B1", speed=80, creature_id=2),)

    result = simulator.run(team_a, team_b)

    step_types = [step.step_type.value for step in result.steps]
    assert "start" in step_types
    assert "victory" in step_types
