from __future__ import annotations

import random

from core.battle.engine.battle_fighter import BattleFighter
from core.battle.engine.battle_result import BattleResult
from core.battle.engine.battle_step import BattleStep, BattleStepType
from core.battle.engine.battle_team_state import BattleSideState, RandomSource
from core.battle.ports.damage_calculator import DamageCalculator


class _PythonRandomSource:
    def randint(self, a: int, b: int) -> int:
        return random.randint(a, b)

    def random(self) -> float:
        return random.random()

    def sample(self, population: list, k: int) -> list:
        return random.sample(population, k)


class BattleSimulator:
    """Local Gen 9 battle simulator — framework agnostic."""

    def __init__(
        self,
        damage_calculator: DamageCalculator,
        *,
        random_source: RandomSource | None = None,
    ) -> None:
        self._damage_calculator = damage_calculator
        self._random = random_source or _PythonRandomSource()

    def run(
        self,
        team_a: tuple[BattleFighter, ...],
        team_b: tuple[BattleFighter, ...],
        *,
        side_a_name: str = "Player 1",
        side_b_name: str = "Player 2",
        side_a_trainer_id: int | None = None,
        side_b_trainer_id: int | None = None,
    ) -> BattleResult:
        side_a = BattleSideState(name=side_a_name, fighters=team_a)
        side_b = BattleSideState(name=side_b_name, fighters=team_b)
        steps: list[BattleStep] = []
        turn = 0

        while True:
            winner = self._check_winner(side_a, side_b)
            if winner is not None:
                steps.append(
                    self._step(
                        BattleStepType.VICTORY,
                        side_a,
                        side_b,
                        f"{winner} wins the battle!",
                    )
                )
                winner_trainer_id = (
                    side_a_trainer_id if winner == side_a_name else side_b_trainer_id
                )
                return BattleResult(
                    steps=tuple(steps),
                    winner_side_name=winner,
                    winner_trainer_id=winner_trainer_id,
                )

            turn += 1
            initial_active = {
                side_a.name: side_a.active_index,
                side_b.name: side_b.active_index,
            }

            if turn == 1:
                steps.append(
                    self._step(
                        BattleStepType.START,
                        side_a,
                        side_b,
                        (
                            f"{side_a.active.display_name} vs "
                            f"{side_b.active.display_name} — battle start!"
                        ),
                    )
                )

            order = self._turn_order(side_a, side_b)

            for attacker_side, defender_side in order:
                if attacker_side.active_index != initial_active[attacker_side.name]:
                    continue

                if attacker_side.hp[attacker_side.active_index] <= 0:
                    continue

                if defender_side.hp[defender_side.active_index] <= 0:
                    continue

                attacker = attacker_side.active
                defender = defender_side.active

                steps.append(
                    self._step(
                        BattleStepType.MOVE,
                        side_a,
                        side_b,
                        f"{attacker_side.name}'s {attacker.display_name} "
                        f"uses {attacker.move_display_name}!",
                    )
                )

                damage_result = self._damage_calculator.calculate(
                    attacker,
                    defender,
                    random_source=self._random,
                )

                steps.append(
                    self._step(
                        BattleStepType.DAMAGE,
                        side_a,
                        side_b,
                        damage_result.message,
                    )
                )

                if damage_result.hit and damage_result.damage > 0:
                    defender_index = defender_side.active_index
                    defender_side.hp[defender_index] = max(
                        0,
                        defender_side.hp[defender_index] - damage_result.damage,
                    )

                attack_message = (
                    f"It dealt {damage_result.damage} damage!"
                    if damage_result.hit
                    else "The attack missed!"
                )
                steps.append(
                    self._step(
                        BattleStepType.ATTACK,
                        side_a,
                        side_b,
                        attack_message,
                    )
                )

                if defender_side.hp[defender_side.active_index] <= 0:
                    winner = self._check_winner(side_a, side_b)
                    if winner is not None:
                        steps.append(
                            self._step(
                                BattleStepType.VICTORY,
                                side_a,
                                side_b,
                                f"{winner} wins the battle!",
                            )
                        )
                        winner_trainer_id = (
                            side_a_trainer_id
                            if winner == side_a_name
                            else side_b_trainer_id
                        )
                        return BattleResult(
                            steps=tuple(steps),
                            winner_side_name=winner,
                            winner_trainer_id=winner_trainer_id,
                        )

                    switched = defender_side.switch_to_next()
                    if switched is None:
                        continue

                    steps.append(
                        self._step(
                            BattleStepType.SWITCH,
                            side_a,
                            side_b,
                            (
                                f"{defender_side.name} sends out "
                                f"{switched.display_name}!"
                            ),
                        )
                    )

    def _turn_order(
        self,
        side_a: BattleSideState,
        side_b: BattleSideState,
    ) -> list[tuple[BattleSideState, BattleSideState]]:
        speed_a = side_a.active.speed
        speed_b = side_b.active.speed

        if speed_a > speed_b:
            return [(side_a, side_b), (side_b, side_a)]

        if speed_b > speed_a:
            return [(side_b, side_a), (side_a, side_b)]

        first, second = self._random.sample([side_a, side_b], 2)
        return [(first, second), (second, first)]

    def _check_winner(
        self,
        side_a: BattleSideState,
        side_b: BattleSideState,
    ) -> str | None:
        if side_a.total_hp <= 0:
            return side_b.name

        if side_b.total_hp <= 0:
            return side_a.name

        return None

    def _step(
        self,
        step_type: BattleStepType,
        side_a: BattleSideState,
        side_b: BattleSideState,
        message: str,
    ) -> BattleStep:
        return BattleStep(
            step_type=step_type,
            side_a_name=side_a.name,
            side_b_name=side_b.name,
            message=message,
            state_snapshot={
                side_a.name: side_a.snapshot(),
                side_b.name: side_b.snapshot(),
            },
        )
