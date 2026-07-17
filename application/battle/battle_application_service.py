from application.battle.exceptions import BattleCreatureNotOnTeam, BattleNotFound
from core.battle.battle import PARTY_SIZE, Battle
from core.battle.battle_repository import BattleRepository
from core.battle.exceptions import (
    InsufficientTeamSize,
    InvalidBattleParty,
    InvalidBattleState,
    SameBattleParticipant,
)
from core.creature.creature_repository import CreatureRepository
from core.team.team_repository import TeamRepository


class BattleApplicationService:
    MIN_TEAM_SIZE = 3
    SELECTION_TIMEOUT_SECONDS = 180

    def __init__(
        self,
        battle_repository: BattleRepository,
        team_repository: TeamRepository,
        creature_repository: CreatureRepository,
    ) -> None:
        self._battle_repository = battle_repository
        self._team_repository = team_repository
        self._creature_repository = creature_repository

    async def create_challenge(
        self,
        initiator_trainer_id: int,
        opponent_trainer_id: int,
        created_at,
    ) -> Battle:
        if initiator_trainer_id == opponent_trainer_id:
            raise SameBattleParticipant()

        await self._ensure_team_size(initiator_trainer_id)
        await self._ensure_team_size(opponent_trainer_id)

        battle = Battle.create(
            initiator_trainer_id=initiator_trainer_id,
            opponent_trainer_id=opponent_trainer_id,
            created_at=created_at,
        )
        return await self._battle_repository.save(battle)

    async def get_battle(self, battle_id: int) -> Battle:
        battle = await self._battle_repository.get(battle_id)
        if battle is None:
            raise BattleNotFound(battle_id)
        return battle

    async def get_team_selector(
        self,
        trainer_id: int,
    ) -> list[tuple[int, str]]:
        team_slots = await self._team_repository.get_by_trainer(trainer_id)
        if not team_slots:
            return []

        creature_ids = [slot.creature_id for slot in team_slots]
        creatures = await self._creature_repository.get_many(creature_ids)
        creatures_by_id = {creature.id: creature for creature in creatures}

        options: list[tuple[int, str]] = []
        for team_slot in team_slots:
            creature = creatures_by_id.get(team_slot.creature_id)
            if creature is None or creature.collection_number is None:
                continue
            label = creature.species.name.title()
            if creature.is_shiny:
                label = f"✨ {label}"
            label = f"#{creature.collection_number} {label}"
            options.append((creature.collection_number, label))

        return options

    async def set_party_from_collection_numbers(
        self,
        battle_id: int,
        trainer_id: int,
        collection_numbers: list[int],
    ) -> Battle:
        if len(collection_numbers) != PARTY_SIZE:
            raise InvalidBattleParty(
                f"Battle party must contain exactly {PARTY_SIZE} creatures."
            )

        creature_ids: list[int] = []
        for collection_number in collection_numbers:
            try:
                creature = await self._creature_repository.get_by_collection_number(
                    trainer_id,
                    collection_number,
                )
            except (KeyError, ValueError) as error:
                raise BattleCreatureNotOnTeam(collection_number) from error

            team_slot = await self._team_repository.get_by_creature_id(
                trainer_id,
                creature.id,
            )
            if team_slot is None:
                raise BattleCreatureNotOnTeam(collection_number)
            creature_ids.append(creature.id)

        return await self.set_party(
            battle_id,
            trainer_id,
            tuple(creature_ids),
        )

    async def set_party(
        self,
        battle_id: int,
        trainer_id: int,
        creature_ids: tuple[int, ...],
    ) -> Battle:
        battle = await self.get_battle(battle_id)

        for creature_id in creature_ids:
            team_slot = await self._team_repository.get_by_creature_id(
                trainer_id,
                creature_id,
            )
            if team_slot is None:
                raise BattleCreatureNotOnTeam(creature_id)

        battle.set_party(trainer_id, creature_ids)
        return await self._battle_repository.save(battle)

    async def start_battle(self, battle_id: int) -> Battle:
        battle = await self.get_battle(battle_id)
        battle.start()
        return await self._battle_repository.save(battle)

    async def complete_battle(
        self,
        battle_id: int,
        winner_trainer_id: int,
    ) -> Battle:
        battle = await self.get_battle(battle_id)
        battle.complete(winner_trainer_id)
        return await self._battle_repository.save(battle)

    async def cancel_battle(
        self,
        battle_id: int,
        actor_trainer_id: int,
    ) -> Battle:
        battle = await self.get_battle(battle_id)
        battle.cancel(actor_trainer_id)
        return await self._battle_repository.save(battle)

    async def get_party_creature_ids(
        self,
        battle_id: int,
        trainer_id: int,
    ) -> tuple[int, ...]:
        battle = await self.get_battle(battle_id)
        party = battle.party_for(trainer_id)
        if party is None:
            raise InvalidBattleState()
        return party

    async def _ensure_team_size(self, trainer_id: int) -> None:
        team_size = await self._team_repository.count_by_trainer(trainer_id)
        if team_size < self.MIN_TEAM_SIZE:
            raise InsufficientTeamSize(trainer_id, self.MIN_TEAM_SIZE)
