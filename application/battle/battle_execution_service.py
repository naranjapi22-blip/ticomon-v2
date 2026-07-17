import asyncio

from application.battle.battle_application_service import BattleApplicationService
from application.battle.creature_fighter_adapter import CreatureFighterAdapter
from core.battle.engine.battle_result import BattleResult
from core.battle.engine.battle_simulator import BattleSimulator
from core.creature.creature_repository import CreatureRepository


class BattleExecutionService:
    def __init__(
        self,
        battle_application_service: BattleApplicationService,
        creature_repository: CreatureRepository,
        creature_fighter_adapter: CreatureFighterAdapter,
        battle_simulator: BattleSimulator,
    ) -> None:
        self._battle_application_service = battle_application_service
        self._creature_repository = creature_repository
        self._creature_fighter_adapter = creature_fighter_adapter
        self._battle_simulator = battle_simulator

    async def run_battle(
        self,
        battle_id: int,
        *,
        initiator_display_name: str,
        opponent_display_name: str,
    ) -> BattleResult:
        battle = await self._battle_application_service.get_battle(battle_id)

        initiator_ids = await self._battle_application_service.get_party_creature_ids(
            battle_id,
            battle.initiator_trainer_id,
        )
        opponent_ids = await self._battle_application_service.get_party_creature_ids(
            battle_id,
            battle.opponent_trainer_id,
        )

        initiator_creatures = await self._load_creatures(initiator_ids)
        opponent_creatures = await self._load_creatures(opponent_ids)

        team_a = self._creature_fighter_adapter.build_many(initiator_creatures)
        team_b = self._creature_fighter_adapter.build_many(opponent_creatures)

        await self._battle_application_service.start_battle(battle_id)

        result = await asyncio.to_thread(
            self._battle_simulator.run,
            team_a,
            team_b,
            side_a_name=initiator_display_name,
            side_b_name=opponent_display_name,
            side_a_trainer_id=battle.initiator_trainer_id,
            side_b_trainer_id=battle.opponent_trainer_id,
        )

        if result.winner_trainer_id is not None:
            await self._battle_application_service.complete_battle(
                battle_id,
                result.winner_trainer_id,
            )

        return result

    async def _load_creatures(
        self,
        creature_ids: tuple[int, ...],
    ):
        creatures = await self._creature_repository.get_many(list(creature_ids))
        creatures_by_id = {creature.id: creature for creature in creatures}
        return [creatures_by_id[creature_id] for creature_id in creature_ids]
