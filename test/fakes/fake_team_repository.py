from core.team.team_repository import TeamRepository
from core.team.team_slot import TeamSlot


class FakeTeamRepository(TeamRepository):
    """
    In-memory team repository for tests.
    """

    def __init__(self) -> None:
        self._slots: dict[tuple[int, int], TeamSlot] = {}
        self._next_id = 1
        self.assigned_queries: list[tuple[int, list[int]]] = []

    async def get_by_trainer(
        self,
        trainer_id: int,
    ) -> list[TeamSlot]:
        return sorted(
            [
                team_slot
                for (stored_trainer_id, _), team_slot in self._slots.items()
                if stored_trainer_id == trainer_id
            ],
            key=lambda team_slot: team_slot.slot,
        )

    async def get_by_creature_id(
        self,
        trainer_id: int,
        creature_id: int,
    ) -> TeamSlot | None:
        for team_slot in self._slots.values():
            if (
                team_slot.trainer_id == trainer_id
                and team_slot.creature_id == creature_id
            ):
                return team_slot
        return None

    async def get_assigned_creature_ids(
        self,
        trainer_id: int,
        creature_ids: list[int] | tuple[int, ...],
    ) -> set[int]:
        requested_ids = list(creature_ids)
        self.assigned_queries.append((trainer_id, requested_ids))
        requested = set(requested_ids)
        return {
            team_slot.creature_id
            for team_slot in self._slots.values()
            if team_slot.trainer_id == trainer_id and team_slot.creature_id in requested
        }

    async def count_by_trainer(
        self,
        trainer_id: int,
    ) -> int:
        return len(await self.get_by_trainer(trainer_id))

    async def add(
        self,
        trainer_id: int,
        slot: int,
        creature_id: int,
    ) -> TeamSlot:
        team_slot = TeamSlot(
            id=self._next_id,
            trainer_id=trainer_id,
            slot=slot,
            creature_id=creature_id,
        )
        self._next_id += 1
        self._slots[(trainer_id, slot)] = team_slot
        return team_slot

    async def replace_creature(
        self,
        trainer_id: int,
        old_creature_id: int,
        new_creature_id: int,
    ) -> TeamSlot:
        current_slot = await self.get_by_creature_id(trainer_id, old_creature_id)
        if current_slot is None:
            raise ValueError(
                f"Creature {old_creature_id} is not assigned to trainer {trainer_id}."
            )

        updated_slot = TeamSlot(
            id=current_slot.id,
            trainer_id=trainer_id,
            slot=current_slot.slot,
            creature_id=new_creature_id,
        )
        self._slots[(trainer_id, current_slot.slot)] = updated_slot
        return updated_slot

    async def remove_by_creature_id(
        self,
        trainer_id: int,
        creature_id: int,
    ) -> None:
        current_slot = await self.get_by_creature_id(trainer_id, creature_id)
        if current_slot is None:
            return

        self._slots.pop((trainer_id, current_slot.slot), None)
