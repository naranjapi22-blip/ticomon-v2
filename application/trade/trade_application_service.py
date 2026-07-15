import logging
from datetime import datetime
from types import MappingProxyType

from application.trade.exceptions import (
    TradeCreatureNotFound,
    TradeCreatureNotOwned,
    TradeNotFound,
    TradeTrainerNotFound,
)
from application.trade.results import AcceptTradeResult
from core.achievement.activity import AchievementActivity, AchievementActivityType
from core.creature.creature_repository import CreatureRepository
from core.trade.exceptions import TradeOfferMustContainExactlyOneCreature
from core.trade.trade import Trade
from core.trade.trade_repository import TradeRepository
from core.trainer.repository import TrainerRepository

logger = logging.getLogger(__name__)


class TradeApplicationService:
    """Coordinates trade negotiation use cases."""

    def __init__(
        self,
        trade_repository: TradeRepository,
        trainer_repository: TrainerRepository,
        creature_repository: CreatureRepository,
        achievement_award_service=None,
    ) -> None:
        self._trade_repository = trade_repository
        self._trainer_repository = trainer_repository
        self._creature_repository = creature_repository
        self._achievement_award_service = achievement_award_service

    async def create_trade(
        self,
        initiator_trainer_id: int,
        counterparty_trainer_id: int,
        initiator_creature_id: int,
        created_at: datetime,
        expires_at: datetime | None = None,
    ) -> AcceptTradeResult:
        await self._ensure_trainers_exist(
            initiator_trainer_id,
            counterparty_trainer_id,
        )
        await self._prevalidate_offer_ownership(
            initiator_trainer_id,
            [initiator_creature_id],
        )

        trade = Trade.create(
            initiator_trainer_id=initiator_trainer_id,
            counterparty_trainer_id=counterparty_trainer_id,
            initiator_creature_id=initiator_creature_id,
            created_at=created_at,
            expires_at=expires_at,
        )

        return await self._trade_repository.save(trade)

    async def create_trade_from_collection_number(
        self,
        initiator_trainer_id: int,
        counterparty_trainer_id: int,
        initiator_collection_number: int,
        created_at: datetime,
        expires_at: datetime | None = None,
    ) -> Trade:
        initiator_creature_id = (
            await self._resolve_collection_numbers(
                initiator_trainer_id,
                [initiator_collection_number],
            )
        )[0]

        return await self.create_trade(
            initiator_trainer_id=initiator_trainer_id,
            counterparty_trainer_id=counterparty_trainer_id,
            initiator_creature_id=initiator_creature_id,
            created_at=created_at,
            expires_at=expires_at,
        )

    async def create_trade_from_collection_numbers(
        self,
        initiator_trainer_id: int,
        counterparty_trainer_id: int,
        initiator_collection_numbers: list[int] | tuple[int, ...],
        created_at: datetime,
        expires_at: datetime | None = None,
    ) -> Trade:
        if len(initiator_collection_numbers) != 1:
            raise TradeOfferMustContainExactlyOneCreature()

        return await self.create_trade_from_collection_number(
            initiator_trainer_id=initiator_trainer_id,
            counterparty_trainer_id=counterparty_trainer_id,
            initiator_collection_number=initiator_collection_numbers[0],
            created_at=created_at,
            expires_at=expires_at,
        )

    async def set_offer(
        self,
        trade_id: int,
        trainer_id: int,
        creature_id: int,
        at: datetime,
    ) -> Trade:
        trade = await self._get_trade(trade_id)
        await self._prevalidate_offer_ownership(
            trainer_id,
            [creature_id],
        )

        trade.set_offer(
            actor_trainer_id=trainer_id,
            creature_id=creature_id,
            at=at,
        )

        return await self._trade_repository.save(trade)

    async def set_offer_from_collection_number(
        self,
        trade_id: int,
        trainer_id: int,
        collection_number: int,
        at: datetime,
    ) -> Trade:
        creature_id = (
            await self._resolve_collection_numbers(
                trainer_id,
                [collection_number],
            )
        )[0]

        return await self.set_offer(
            trade_id=trade_id,
            trainer_id=trainer_id,
            creature_id=creature_id,
            at=at,
        )

    async def set_offer_from_collection_numbers(
        self,
        trade_id: int,
        trainer_id: int,
        collection_numbers: list[int] | tuple[int, ...],
        at: datetime,
    ) -> Trade:
        if len(collection_numbers) != 1:
            raise TradeOfferMustContainExactlyOneCreature()

        return await self.set_offer_from_collection_number(
            trade_id=trade_id,
            trainer_id=trainer_id,
            collection_number=collection_numbers[0],
            at=at,
        )

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
            return AcceptTradeResult(await self._trade_repository.save(trade))

        trade.assert_ready_to_execute(at)

        activities, species_by_trainer = await self._completed_trade_activities(trade)
        completed_trade = await self._trade_repository.execute_completed_trade(
            trade,
            completed_at=at,
            activities=activities,
        )
        achievements = await self._award_completed_trade(species_by_trainer)
        return AcceptTradeResult(completed_trade, achievements)

    async def _completed_trade_activities(self, trade: Trade):
        assert trade.id is not None
        assert trade.counterparty_offer is not None
        offers = (trade.initiator_offer, trade.counterparty_offer)
        activities = []
        species_by_trainer = {}
        for offer in offers:
            creature = await self._creature_repository.get(offer.creature_id)
            species_by_trainer[offer.trainer_id] = creature.species
            activities.append(
                AchievementActivity(
                    trainer_id=offer.trainer_id,
                    activity_type=AchievementActivityType.COMPLETED_TRADE,
                    species_id=creature.species.id,
                    idempotency_key=(f"trade:{trade.id}:trainer:{offer.trainer_id}"),
                )
            )
        return tuple(activities), species_by_trainer

    async def _award_completed_trade(self, species_by_trainer):
        if self._achievement_award_service is None:
            return MappingProxyType({})
        results = {}
        for trainer_id, species in species_by_trainer.items():
            try:
                unlocks = (
                    await self._achievement_award_service.award_for_completed_trade(
                        trainer_id,
                        species,
                    )
                )
            except Exception:
                logger.exception(
                    "trade achievement award failed trainer_id=%s",
                    trainer_id,
                )
                continue
            if unlocks:
                results[trainer_id] = unlocks
        return MappingProxyType(results)

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

    async def _resolve_collection_numbers(
        self,
        trainer_id: int,
        collection_numbers: list[int] | tuple[int, ...],
    ) -> list[int]:
        creature_ids: list[int] = []

        for collection_number in collection_numbers:
            try:
                creature = await self._creature_repository.get_by_collection_number(
                    trainer_id,
                    collection_number,
                )
            except KeyError as error:
                raise TradeCreatureNotFound(collection_number) from error
            except ValueError as error:
                raise TradeCreatureNotOwned(trainer_id, collection_number) from error

            creature_ids.append(creature.id)

        return creature_ids
