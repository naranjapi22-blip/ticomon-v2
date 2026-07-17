from __future__ import annotations

import logging

from poke_env.battle import Battle
from poke_env.battle.move import Move
from poke_env.calc import damage_calc_gen9 as calc_gen9

from core.battle.engine.battle_fighter import BattleFighter
from core.battle.engine.battle_team_state import RandomSource
from core.battle.ports.damage_calculator import DamageCalculator, DamageResult

logger = logging.getLogger(__name__)

ATTACKER_ID = "p1a: Attacker"
DEFENDER_ID = "p2a: Defender"


def effectiveness_label(multiplier: float) -> str:
    if multiplier == 0:
        return "It doesn't affect the target..."
    if multiplier >= 2:
        return "It's super effective!"
    if 0 < multiplier <= 0.5:
        return "It's not very effective..."
    return ""


class PokeEnvDamageCalculator(DamageCalculator):
    """Gen 9 damage calculation via poke-env."""

    def calculate(
        self,
        attacker: BattleFighter,
        defender: BattleFighter,
        *,
        random_source: RandomSource,
    ) -> DamageResult:
        move = Move(attacker.move_id, gen=9)
        accuracy = move.accuracy
        if accuracy is True or accuracy is None:
            acc_pct = 100
        else:
            acc_pct = int(accuracy) if int(accuracy) > 1 else int(accuracy * 100)

        if acc_pct < 100 and random_source.randint(1, 100) > acc_pct:
            return DamageResult(
                damage=0,
                hit=False,
                critical=False,
                effectiveness_label="",
                message=f"{attacker.display_name}'s attack missed!",
            )

        is_critical = random_source.randint(1, 24) == 1

        try:
            battle = self._build_battle(attacker, defender)
            damage_range = calc_gen9.calculate_damage(
                ATTACKER_ID,
                DEFENDER_ID,
                move,
                battle,
                is_critical=is_critical,
            )
            damage_min, damage_max = damage_range
            if damage_min == damage_max:
                damage = damage_min
            else:
                damage = random_source.randint(damage_min, damage_max)

            defender_pokemon = battle.get_pokemon(DEFENDER_ID)
            effectiveness = 1.0
            for defender_type in defender_pokemon.types:
                effectiveness *= calc_gen9.get_move_effectiveness(
                    move,
                    move.type,
                    defender_type,
                )
            label = effectiveness_label(effectiveness)

            message_parts = [
                f"{attacker.display_name} used {attacker.move_display_name}!",
            ]
            if is_critical:
                message_parts.append("A critical hit!")
            if label:
                message_parts.append(label)

            return DamageResult(
                damage=max(0, damage),
                hit=True,
                critical=is_critical,
                effectiveness_label=label,
                message=" ".join(message_parts),
            )
        except Exception as error:
            logger.warning("Showdown damage calc failed, using fallback: %s", error)
            return self._fallback_damage(attacker, defender, random_source)

    def _build_battle(
        self,
        attacker: BattleFighter,
        defender: BattleFighter,
    ) -> Battle:
        battle = Battle(
            battle_tag="ticomon-local",
            username="p1",
            logger=logger,
            gen=9,
        )
        battle._player_role = "p1"
        battle._opponent_role = "p2"

        attacker_pokemon = battle.get_pokemon(
            ATTACKER_ID,
            details=attacker.species_showdown_id,
        )
        defender_pokemon = battle.get_pokemon(
            DEFENDER_ID,
            details=defender.species_showdown_id,
        )

        attacker_pokemon._stats = {
            "hp": attacker.hp_max,
            "atk": attacker.attack,
            "def": attacker.defense,
            "spa": attacker.special_attack,
            "spd": attacker.special_defense,
            "spe": attacker.speed,
        }
        defender_pokemon._stats = {
            "hp": defender.hp_max,
            "atk": defender.attack,
            "def": defender.defense,
            "spa": defender.special_attack,
            "spd": defender.special_defense,
            "spe": defender.speed,
        }
        attacker_pokemon._level = 50
        defender_pokemon._level = 50
        attacker_pokemon._active = True
        defender_pokemon._active = True

        return battle

    def _fallback_damage(
        self,
        attacker: BattleFighter,
        defender: BattleFighter,
        random_source: RandomSource,
    ) -> DamageResult:
        offensive_stat = max(attacker.attack, attacker.special_attack)
        defensive_stat = max(defender.defense, defender.special_defense)
        damage = max(
            3,
            int(
                (offensive_stat / (defensive_stat + 15))
                * 25
                * (0.85 + random_source.random() * 0.15)
            ),
        )
        return DamageResult(
            damage=damage,
            hit=True,
            critical=False,
            effectiveness_label="",
            message=f"{attacker.display_name} used {attacker.move_display_name}!",
        )
