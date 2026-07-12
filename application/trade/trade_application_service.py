from datetime import datetime

from application.trade.exceptions import (
    TradeCreatureNotFound,
    TradeCreatureNotOwned,
    TradeNotFound,
    TradeTrainerNotFound,
)
from core.creature.creature_repository import CreatureRepository
from core.trade.trade import Trade
from core.trade.trade_repository import TradeRepository
from core.trainer.repository import TrainerRepository


class TradeApplicationService:
    """Coordinates trade negotiation use cases."""

    def __init__(
        self,
        trade_repository: TradeRepository,
        trainer_repository: TrainerRepository,
        creature_repository: CreatureRepository,
    ) -> None:
        self._trade_repository = trade_repository
        self._trainer_repository = trainer_repository
        self._creature_repository = creature_repository

    async def create_trade(
        self,
        initiator_trainer_id: int,
        counterparty_trainer_id: int,
        initiator_creature_ids: list[int] | tuple[int, ...],
        created_at: datetime,
        expires_at: datetime | None = None,
    ) -> Trade:
        await self._ensure_trainers_exist(
            initiator_trainer_id,
            counterparty_trainer_id,
        )
        await self._prevalidate_offer_ownership(
            initiator_trainer_id,
            initiator_creature_ids,
        )

        trade = Trade.create(
            initiator_trainer_id=initiator_trainer_id,
            counterparty_trainer_id=counterparty_trainer_id,
            initiator_creature_ids=initiator_creature_ids,
            created_at=created_at,
            expires_at=expires_at,
        )

        return await self._trade_repository.save(trade)

    async def set_offer(
        self,
        trade_id: int,
        trainer_id: int,
        creature_ids: list[int] | tuple[int, ...],
        at: datetime,
    ) -> Trade:
        trade = await self._get_trade(trade_id)
        await self._prevalidate_offer_ownership(
            trainer_id,
            creature_ids,
        )

        trade.set_offer(
            actor_trainer_id=trainer_id,
            creature_ids=creature_ids,
            at=at,
        )

        return await self._trade_repository.save(trade)

    async def accept_trade(
        self,
        trade_id: int,
        trainer_id: int,
        at: datetime,
    ) -> Trade:
        trade = await self._get_trade(trade_id)
        trade.accept(
            actor_trainer_id=trainer_id,
            at=at,
        )

        if not trade.is_ready_to_execute:
            return await self._trade_repository.save(trade)

        trade.assert_ready_to_execute(at)

        return await self._trade_repository.execute_completed_trade(
            trade,
            completed_at=at,
        )

    async def cancel_trade(
        self,
        trade_id: int,
        trainer_id: int,
        at: datetime,
    ) -> Trade:
        trade = await self._get_trade(trade_id)
        trade.cancel(
            actor_trainer_id=trainer_id,
            at=at,
        )
        return await self._trade_repository.save(trade)

    async def reject_trade(
        self,
        trade_id: int,
        trainer_id: int,
        at: datetime,
    ) -> Trade:
        trade = await self._get_trade(trade_id)
        trade.reject(
            actor_trainer_id=trainer_id,
            at=at,
        )
        return await self._trade_repository.save(trade)

    async def get_trade(self, trade_id: int) -> Trade:
        return await self._get_trade(trade_id)

    async def _get_trade(self, trade_id: int) -> Trade:
        trade = await self._trade_repository.get(trade_id)

        if trade is None:
            raise TradeNotFound(trade_id)

        return trade

    async def _ensure_trainers_exist(
        self,
        initiator_trainer_id: int,
        counterparty_trainer_id: int,
    ) -> None:
        if not await self._trainer_repository.exists(initiator_trainer_id):
            raise TradeTrainerNotFound(initiator_trainer_id)

        if not await self._trainer_repository.exists(counterparty_trainer_id):
            raise TradeTrainerNotFound(counterparty_trainer_id)

    async def _prevalidate_offer_ownership(
        self,
        trainer_id: int,
        creature_ids: list[int] | tuple[int, ...],
    ) -> None:
        """Checks current ownership for early feedback only.

        TradeRepository.execute_completed_trade() must repeat this validation
        inside its atomic operation because ownership may change afterwards.
        """

        for creature_id in creature_ids:
            try:
                creature = await self._creature_repository.get(creature_id)
            except (KeyError, ValueError) as error:
                raise TradeCreatureNotFound(creature_id) from error

            if creature is None:
                raise TradeCreatureNotFound(creature_id)

            if creature.trainer_id != trainer_id:
                raise TradeCreatureNotOwned(
                    trainer_id,
                    creature_id,
                )
