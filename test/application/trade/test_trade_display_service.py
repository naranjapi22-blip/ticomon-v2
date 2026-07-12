from datetime import UTC, datetime

import pytest

from application.trade.exceptions import TradeNotFound
from application.trade.trade_display_service import TradeDisplayService
from core.creature.nature import Nature
from core.creature.size import Size
from core.species.variant import Variant
from core.trade.trade import Trade
from core.trade.trade_offer import TradeOffer
from core.trade.trade_status import TradeStatus
from test.builders.creature_builder import CreatureBuilder
from test.builders.species_builder import SpeciesBuilder
from test.fakes.fake_creature_repository import FakeCreatureRepository
from test.fakes.fake_trade_repository import FakeTradeRepository

NOW = datetime(2026, 7, 12, 12, 0, 0, tzinfo=UTC)


def _make_creature(
    *,
    creature_id: int,
    trainer_id: int,
    collection_number: int,
    species_name: str,
    is_shiny: bool = False,
    current_form_name: str | None = None,
) -> object:
    creature = (
        CreatureBuilder()
        .with_id(creature_id)
        .with_trainer_id(trainer_id)
        .with_collection_number(collection_number)
        .with_species(SpeciesBuilder().with_name(species_name).build())
        .build()
    )
    creature.is_shiny = is_shiny
    creature.nature = Nature("jolly")
    creature.size = Size(1.12)
    creature.current_form = (
        Variant(id=1, name=current_form_name) if current_form_name is not None else None
    )
    return creature


def _make_trade() -> Trade:
    return Trade._reconstitute(
        trade_id=42,
        initiator_trainer_id=101,
        counterparty_trainer_id=202,
        initiator_offer=TradeOffer.create(101, 11),
        counterparty_offer=TradeOffer.create(202, 22),
        created_at=NOW,
        expires_at=None,
        status=TradeStatus.OPEN,
        initiator_accepted_at=NOW,
        counterparty_accepted_at=None,
        completed_at=None,
    )


@pytest.mark.asyncio
async def test_get_trade_display_builds_creature_details() -> None:
    initiator_creature = _make_creature(
        creature_id=11,
        trainer_id=101,
        collection_number=7,
        species_name="pikachu",
        is_shiny=True,
        current_form_name="Rockstar",
    )
    counterparty_creature = _make_creature(
        creature_id=22,
        trainer_id=202,
        collection_number=14,
        species_name="eevee",
    )
    creature_repository = FakeCreatureRepository(
        initiator_creature,
        counterparty_creature,
    )
    trade_repository = FakeTradeRepository(creature_repository)
    trade = await trade_repository.save(_make_trade())

    display = await TradeDisplayService(
        trade_repository=trade_repository,
        creature_repository=creature_repository,
    ).get_trade_display(trade.id)

    assert display.trade_id == 42
    assert display.status is TradeStatus.OPEN
    assert display.initiator_offer.creature is not None
    assert display.initiator_offer.creature.species_name == "Pikachu"
    assert display.initiator_offer.creature.collection_number == 7
    assert display.initiator_offer.creature.iv_percentage == 100
    assert display.initiator_offer.creature.is_shiny is True
    assert display.initiator_offer.creature.nature == "Jolly"
    assert display.initiator_offer.creature.size == "L (1.12×)"
    assert display.initiator_offer.creature.current_form_name == "Rockstar"
    assert display.counterparty_offer is not None
    assert display.counterparty_offer.creature is not None
    assert display.counterparty_offer.creature.species_name == "Eevee"
    assert display.initiator_offer.accepted_at == NOW
    assert display.counterparty_offer.accepted_at is None


@pytest.mark.asyncio
async def test_get_trade_display_rejects_unknown_trade() -> None:
    creature_repository = FakeCreatureRepository()
    trade_repository = FakeTradeRepository(creature_repository)

    with pytest.raises(TradeNotFound):
        await TradeDisplayService(
            trade_repository=trade_repository,
            creature_repository=creature_repository,
        ).get_trade_display(99)
