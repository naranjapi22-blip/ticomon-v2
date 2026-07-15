from __future__ import annotations

from typing import Iterable


class NotEnoughSafariBalls(ValueError):
    pass


class SafariParticipant:
    def __init__(
        self,
        trainer_id: int,
        initial_balls: int,
        remaining_balls: int,
        captured_creature_ids: Iterable[int] = (),
    ) -> None:
        if trainer_id <= 0:
            raise ValueError("trainer_id must be positive.")

        if initial_balls <= 0:
            raise ValueError("initial_balls must be positive.")

        if remaining_balls < 0 or remaining_balls > initial_balls:
            raise ValueError("remaining_balls must be between zero and initial_balls.")

        captures = list(captured_creature_ids)
        if any(creature_id <= 0 for creature_id in captures):
            raise ValueError("captured creature IDs must be positive.")

        self._trainer_id = trainer_id
        self._initial_balls = initial_balls
        self._remaining_balls = remaining_balls
        self._captured_creature_ids = captures

    @property
    def trainer_id(self) -> int:
        return self._trainer_id

    @property
    def initial_balls(self) -> int:
        return self._initial_balls

    @property
    def remaining_balls(self) -> int:
        return self._remaining_balls

    @property
    def captured_creature_ids(self) -> tuple[int, ...]:
        return tuple(self._captured_creature_ids)

    @property
    def capture_count(self) -> int:
        return len(self._captured_creature_ids)

    @property
    def balls_spent(self) -> int:
        return self._initial_balls - self._remaining_balls

    @property
    def can_capture(self) -> bool:
        return self._remaining_balls > 0

    def validate_ball_spend(self, amount: int) -> None:
        if amount < 1 or amount > 3:
            raise ValueError("amount must be between 1 and 3.")

        if amount > self._remaining_balls:
            raise NotEnoughSafariBalls("Not enough Safari Balls remaining.")

    def spend_balls(self, amount: int) -> None:
        self.validate_ball_spend(amount)

        self._remaining_balls -= amount

    def record_capture(self, creature_id: int) -> None:
        if creature_id <= 0:
            raise ValueError("creature_id must be positive.")

        self._captured_creature_ids.append(creature_id)
