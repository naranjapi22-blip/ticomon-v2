from datetime import datetime

from core.trade.exceptions import TradeExecutionConflict
from core.trade.trade import Trade
from core.trade.trade_repository import TradeRepository
from core.trade.trade_status import TradeStatus
from test.fakes.fake_creature_repository import FakeCreatureRepository


class FakeTradeRepository(TradeRepository):
    """In-memory trade repository for application-service tests."""

    def __init__(self, creature_repository: FakeCreatureRepository) -> None:
        self._creature_repository = creature_repository
        self._trades: dict[int, Trade] = {}
        self._next_id = 1
        self.execute_calls = 0

    async def save(self, trade: Trade) -> Trade:
        trade_id = trade.id

        if trade_id is None:
            trade_id = self._next_id
            self._next_id += 1

        stored = self._copy(trade, trade_id=trade_id)
        self._trades[trade_id] = stored
        return stored

    async def get(self, trade_id: int) -> Trade | None:
        return self._trades.get(trade_id)

    async def execute_completed_trade(
        self,
        trade: Trade,
        completed_at: datetime,
    ) -> Trade:
        self.execute_calls += 1
        trade.assert_ready_to_execute(completed_at)

        if trade.id is None:
            raise TradeExecutionConflict()

        transfers = (
            (trade.initiator_offer, trade.counterparty_trainer_id),
            (trade.counterparty_offer, trade.initiator_trainer_id),
        )

        creatures = []

        for offer, receiving_trainer_id in transfers:
            assert offer is not None

            for creature_id in offer.creature_ids:
                try:
                    creature = await self._creature_repository.get(creature_id)
                except KeyError as error:
                    raise TradeExecutionConflict() from error

                if creature.trainer_id != offer.trainer_id:
                    raise TradeExecutionConflict()

                creatures.append((creature, receiving_trainer_id))

        if len(creatures) != 2:
            raise TradeExecutionConflict()

        initiator_creature, initiator_receiving_trainer_id = creatures[0]
        counterparty_creature, counterparty_receiving_trainer_id = creatures[1]

        initiator_creature.trainer_id = initiator_receiving_trainer_id
        counterparty_creature.trainer_id = counterparty_receiving_trainer_id
        (
            initiator_creature.collection_number,
            counterparty_creature.collection_number,
        ) = (
            counterparty_creature.collection_number,
            initiator_creature.collection_number,
        )

        for creature, receiving_trainer_id in creatures:
            creature.trainer_id = receiving_trainer_id
            await self._creature_repository.update(creature)

        completed = self._copy(
            trade,
            trade_id=trade.id,
            status=TradeStatus.COMPLETED,
            completed_at=completed_at,
        )
        self._trades[trade.id] = completed
        return completed

    @staticmethod
    def _copy(
        trade: Trade,
        *,
        trade_id: int,
        status: TradeStatus | None = None,
        completed_at: datetime | None = None,
    ) -> Trade:
        return Trade._reconstitute(
            trade_id=trade_id,
            initiator_trainer_id=trade.initiator_trainer_id,
            counterparty_trainer_id=trade.counterparty_trainer_id,
            initiator_offer=trade.initiator_offer,
            counterparty_offer=trade.counterparty_offer,
            created_at=trade.created_at,
            expires_at=trade.expires_at,
            status=status or trade.status,
            initiator_accepted_at=trade.initiator_accepted_at,
            counterparty_accepted_at=trade.counterparty_accepted_at,
            cancelled_by_trainer_id=trade.cancelled_by_trainer_id,
            rejected_by_trainer_id=trade.rejected_by_trainer_id,
            completed_at=completed_at or trade.completed_at,
        )
