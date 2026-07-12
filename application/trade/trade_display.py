from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from core.trade.trade_status import TradeStatus


@dataclass(frozen=True, slots=True)
class TradeCreatureDisplay:
    creature_id: int
    trainer_id: int
    species_name: str
    collection_number: int
    iv_percentage: int
    is_shiny: bool
    nature: str
    size: str
    current_form_name: str | None = None


@dataclass(frozen=True, slots=True)
class TradeOfferDisplay:
    trainer_id: int
    creature: TradeCreatureDisplay | None
    accepted_at: datetime | None


@dataclass(frozen=True, slots=True)
class TradeDisplay:
    trade_id: int
    status: TradeStatus
    initiator_trainer_id: int
    counterparty_trainer_id: int
    initiator_offer: TradeOfferDisplay
    counterparty_offer: TradeOfferDisplay | None
    completed_at: datetime | None
    cancelled_by_trainer_id: int | None
    rejected_by_trainer_id: int | None
