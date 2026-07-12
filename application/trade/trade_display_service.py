from __future__ import annotations

from datetime import datetime

from application.trade.exceptions import (
    TradeCreatureNotFound,
    TradeNotFound,
)
from application.trade.trade_display import (
    TradeCreatureDisplay,
    TradeDisplay,
    TradeOfferDisplay,
)
from core.creature.creature_repository import CreatureRepository
from core.trade.trade_repository import TradeRepository


class TradeDisplayService:
    def __init__(
        self,
        trade_repository: TradeRepository,
        creature_repository: CreatureRepository,
    ) -> None:
        self._trade_repository = trade_repository
        self._creature_repository = creature_repository

    async def get_trade_display(
        self,
        trade_id: int,
    ) -> TradeDisplay:
        trade = await self._trade_repository.get(trade_id)

        if trade is None:
            raise TradeNotFound(trade_id)
        if trade.id is None:
            raise TradeNotFound(trade_id)

        return TradeDisplay(
            trade_id=trade.id,
            status=trade.status,
            initiator_trainer_id=trade.initiator_trainer_id,
            counterparty_trainer_id=trade.counterparty_trainer_id,
            initiator_offer=(
                await self._build_offer_display(
                    trainer_id=trade.initiator_trainer_id,
                    creature_id=trade.initiator_offer.creature_id,
                    accepted_at=trade.initiator_accepted_at,
                )
            ),
            counterparty_offer=(
                None
                if trade.counterparty_offer is None
                else await self._build_offer_display(
                    trainer_id=trade.counterparty_trainer_id,
                    creature_id=trade.counterparty_offer.creature_id,
                    accepted_at=trade.counterparty_accepted_at,
                )
            ),
            completed_at=trade.completed_at,
            cancelled_by_trainer_id=trade.cancelled_by_trainer_id,
            rejected_by_trainer_id=trade.rejected_by_trainer_id,
        )

    async def _build_offer_display(
        self,
        *,
        trainer_id: int,
        creature_id: int,
        accepted_at: datetime | None,
    ) -> TradeOfferDisplay:
        try:
            creature = await self._creature_repository.get(creature_id)
        except (KeyError, ValueError) as error:
            raise TradeCreatureNotFound(creature_id) from error

        if creature is None:
            raise TradeCreatureNotFound(creature_id)

        return TradeOfferDisplay(
            trainer_id=trainer_id,
            creature=TradeCreatureDisplay(
                creature_id=creature.id,
                trainer_id=creature.trainer_id,
                species_name=creature.species.name.title(),
                collection_number=creature.collection_number,
                iv_percentage=creature.iv_percentage,
                is_shiny=creature.is_shiny,
                nature=str(creature.nature),
                size=str(creature.size),
                current_form_name=(
                    creature.current_form.name if creature.current_form else None
                ),
            ),
            accepted_at=accepted_at,
        )
