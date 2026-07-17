from application.team.exceptions import (
    TeamCreatureAlreadyInTeam,
    TeamCreatureNotFound,
    TeamCreatureNotInTeam,
    TeamCreatureNotOwned,
    TeamFull,
    TeamInsufficientCreatures,
)
from application.team.team_dto import TeamDTO, TeamSlotDTO
from core.creature.creature_repository import CreatureRepository
from core.team.team_repository import TeamRepository


class TeamApplicationService:
    MIN_CREATURES_REQUIRED = 3
    MAX_TEAM_SIZE = 9
    MIN_SLOT = 1
    MAX_SLOT = 9

    def __init__(
        self,
        creature_repository: CreatureRepository,
        team_repository: TeamRepository,
    ) -> None:
        self._creature_repository = creature_repository
        self._team_repository = team_repository

    async def get_team(
        self,
        trainer_id: int,
    ) -> TeamDTO:
        team_slots = await self._team_repository.get_by_trainer(trainer_id)

        if not team_slots:
            return TeamDTO(
                trainer_id=trainer_id,
                slots=(),
            )

        creature_ids = [team_slot.creature_id for team_slot in team_slots]
        creatures = await self._creature_repository.get_many(creature_ids)
        creatures_by_id = {creature.id: creature for creature in creatures}

        return TeamDTO(
            trainer_id=trainer_id,
            slots=tuple(
                TeamSlotDTO(
                    slot=team_slot.slot,
                    creature=creatures_by_id[team_slot.creature_id],
                )
                for team_slot in team_slots
            ),
        )

    async def add_to_team(
        self,
        trainer_id: int,
        collection_number: int,
    ) -> None:
        await self._ensure_minimum_creatures(trainer_id)

        creature = await self._resolve_collection_number(
            trainer_id,
            collection_number,
        )

        if await self._team_repository.get_by_creature_id(trainer_id, creature.id):
            raise TeamCreatureAlreadyInTeam(collection_number)

        team_size = await self._team_repository.count_by_trainer(trainer_id)
        if team_size >= self.MAX_TEAM_SIZE:
            raise TeamFull(self.MAX_TEAM_SIZE)

        slot = await self._next_available_slot(trainer_id)

        await self._team_repository.add(
            trainer_id,
            slot,
            creature.id,
        )

    async def replace_in_team(
        self,
        trainer_id: int,
        collection_number_to_replace: int,
        new_collection_number: int,
    ) -> None:
        await self._ensure_minimum_creatures(trainer_id)

        creature_to_replace = await self._resolve_collection_number(
            trainer_id,
            collection_number_to_replace,
        )
        new_creature = await self._resolve_collection_number(
            trainer_id,
            new_collection_number,
        )

        if creature_to_replace.id == new_creature.id:
            raise TeamCreatureAlreadyInTeam(new_collection_number)

        current_slot = await self._team_repository.get_by_creature_id(
            trainer_id,
            creature_to_replace.id,
        )
        if current_slot is None:
            raise TeamCreatureNotInTeam(collection_number_to_replace)

        if await self._team_repository.get_by_creature_id(trainer_id, new_creature.id):
            raise TeamCreatureAlreadyInTeam(new_collection_number)

        await self._team_repository.replace_creature(
            trainer_id,
            creature_to_replace.id,
            new_creature.id,
        )

    async def remove_from_team(
        self,
        trainer_id: int,
        collection_number: int,
    ) -> None:
        await self._ensure_minimum_creatures(trainer_id)

        creature = await self._resolve_collection_number(
            trainer_id,
            collection_number,
        )

        current_slot = await self._team_repository.get_by_creature_id(
            trainer_id,
            creature.id,
        )
        if current_slot is None:
            raise TeamCreatureNotInTeam(collection_number)

        await self._team_repository.remove_by_creature_id(
            trainer_id,
            creature.id,
        )

    async def _ensure_minimum_creatures(
        self,
        trainer_id: int,
    ) -> None:
        creature_count = await self._creature_repository.count_creatures(trainer_id)
        if creature_count < self.MIN_CREATURES_REQUIRED:
            raise TeamInsufficientCreatures(
                trainer_id,
                self.MIN_CREATURES_REQUIRED,
            )

    async def _next_available_slot(
        self,
        trainer_id: int,
    ) -> int:
        team_slots = await self._team_repository.get_by_trainer(trainer_id)
        occupied_slots = {team_slot.slot for team_slot in team_slots}

        for slot in range(self.MIN_SLOT, self.MAX_SLOT + 1):
            if slot not in occupied_slots:
                return slot

        raise TeamFull(self.MAX_TEAM_SIZE)

    async def _resolve_collection_number(
        self,
        trainer_id: int,
        collection_number: int,
    ):
        try:
            return await self._creature_repository.get_by_collection_number(
                trainer_id,
                collection_number,
            )
        except KeyError as error:
            raise TeamCreatureNotFound(collection_number) from error
        except ValueError as error:
            raise TeamCreatureNotOwned(trainer_id, collection_number) from error
