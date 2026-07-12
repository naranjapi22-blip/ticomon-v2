from datetime import datetime

import pytest

from application.trade.exceptions import (
    TradeCreatureNotFound,
    TradeCreatureNotOwned,
    TradeNotFound,
    TradeTrainerNotFound,
)
from application.trade.trade_application_service import TradeApplicationService
from core.trade.exceptions import TradeOfferMustContainExactlyOneCreature
from core.trade.trade_status import TradeStatus
from core.trainer.trainer import Trainer
from test.builders.creature_builder import CreatureBuilder
from test.fakes.fake_creature_repository import FakeCreatureRepository
from test.fakes.fake_trade_repository import FakeTradeRepository
from test.fakes.fake_trainer_repository import FakeTrainerRepository

NOW = datetime(2026, 7, 12, 12, 0, 0)
INITIATOR_ID = 10
COUNTERPARTY_ID = 20


@pytest.fixture
def service_context():
    initiator_creature = (
        CreatureBuilder()
        .with_id(101)
        .with_trainer_id(INITIATOR_ID)
        .with_collection_number(7)
        .shiny()
        .build()
    )
    counterparty_creature = (
        CreatureBuilder()
        .with_id(202)
        .with_trainer_id(COUNTERPARTY_ID)
        .with_collection_number(14)
        .build()
    )

    creature_repository = FakeCreatureRepository(
        initiator_creature,
        counterparty_creature,
    )
    trainer_repository = FakeTrainerRepository()
    trade_repository = FakeTradeRepository(creature_repository)

    return {
        "service": TradeApplicationService(
            trade_repository=trade_repository,
            trainer_repository=trainer_repository,
            creature_repository=creature_repository,
        ),
        "trainer_repository": trainer_repository,
        "creature_repository": creature_repository,
        "trade_repository": trade_repository,
        "initiator_creature": initiator_creature,
        "counterparty_creature": counterparty_creature,
    }


async def add_trainers(trainer_repository):
    await trainer_repository.save(
        Trainer(
            trainer_id=INITIATOR_ID,
            starter_creature_id=101,
            started_at=NOW,
        )
    )
    await trainer_repository.save(
        Trainer(
            trainer_id=COUNTERPARTY_ID,
            starter_creature_id=202,
            started_at=NOW,
        )
    )


@pytest.mark.asyncio
async def test_creates_persisted_trade_for_existing_owner(service_context):
    await add_trainers(service_context["trainer_repository"])

    trade = await service_context["service"].create_trade_from_collection_number(
        initiator_trainer_id=INITIATOR_ID,
        counterparty_trainer_id=COUNTERPARTY_ID,
        initiator_collection_number=7,
        created_at=NOW,
    )

    assert trade.id == 1
    assert trade.status is TradeStatus.DRAFT
    assert trade.initiator_offer.creature_ids == (101,)


@pytest.mark.asyncio
async def test_creates_trade_from_collection_numbers(service_context):
    await add_trainers(service_context["trainer_repository"])

    trade = await service_context["service"].create_trade_from_collection_number(
        initiator_trainer_id=INITIATOR_ID,
        counterparty_trainer_id=COUNTERPARTY_ID,
        initiator_collection_number=7,
        created_at=NOW,
    )

    assert trade.id == 1
    assert trade.initiator_offer.creature_ids == (101,)


@pytest.mark.asyncio
async def test_create_trade_from_collection_numbers_rejects_multiple_numbers(
    service_context,
):
    await add_trainers(service_context["trainer_repository"])

    with pytest.raises(TradeOfferMustContainExactlyOneCreature):
        await service_context["service"].create_trade_from_collection_numbers(
            initiator_trainer_id=INITIATOR_ID,
            counterparty_trainer_id=COUNTERPARTY_ID,
            initiator_collection_numbers=[7, 14],
            created_at=NOW,
        )


@pytest.mark.asyncio
async def test_rejects_missing_trade_participant(service_context):
    await service_context["trainer_repository"].save(
        Trainer(
            trainer_id=INITIATOR_ID,
            starter_creature_id=101,
            started_at=NOW,
        )
    )

    with pytest.raises(TradeTrainerNotFound) as error:
        await service_context["service"].create_trade_from_collection_number(
            initiator_trainer_id=INITIATOR_ID,
            counterparty_trainer_id=COUNTERPARTY_ID,
            initiator_collection_number=7,
            created_at=NOW,
        )

    assert str(COUNTERPARTY_ID) in str(error.value)


@pytest.mark.asyncio
async def test_rejects_missing_offered_creature(service_context):
    await add_trainers(service_context["trainer_repository"])

    with pytest.raises(TradeCreatureNotFound) as error:
        await service_context["service"].create_trade_from_collection_number(
            initiator_trainer_id=INITIATOR_ID,
            counterparty_trainer_id=COUNTERPARTY_ID,
            initiator_collection_number=999,
            created_at=NOW,
        )

    assert str(999) in str(error.value)


@pytest.mark.asyncio
async def test_rejects_creature_not_owned_by_offering_trainer(service_context):
    await add_trainers(service_context["trainer_repository"])

    with pytest.raises(TradeCreatureNotOwned):
        await service_context["service"].create_trade_from_collection_number(
            initiator_trainer_id=INITIATOR_ID,
            counterparty_trainer_id=COUNTERPARTY_ID,
            initiator_collection_number=14,
            created_at=NOW,
        )


@pytest.mark.asyncio
async def test_set_offer_prevalidates_current_ownership(service_context):
    await add_trainers(service_context["trainer_repository"])
    trade = await service_context["service"].create_trade_from_collection_number(
        initiator_trainer_id=INITIATOR_ID,
        counterparty_trainer_id=COUNTERPARTY_ID,
        initiator_collection_number=7,
        created_at=NOW,
    )

    with pytest.raises(TradeCreatureNotOwned):
        await service_context["service"].set_offer_from_collection_number(
            trade_id=trade.id,
            trainer_id=COUNTERPARTY_ID,
            collection_number=7,
            at=NOW,
        )


@pytest.mark.asyncio
async def test_set_offer_from_collection_numbers_resets_acceptances(
    service_context,
):
    await add_trainers(service_context["trainer_repository"])
    extra_counterparty_creature = (
        CreatureBuilder()
        .with_id(303)
        .with_trainer_id(COUNTERPARTY_ID)
        .with_collection_number(15)
        .build()
    )
    await service_context["creature_repository"].save(
        extra_counterparty_creature,
    )
    trade = await service_context["service"].create_trade_from_collection_number(
        initiator_trainer_id=INITIATOR_ID,
        counterparty_trainer_id=COUNTERPARTY_ID,
        initiator_collection_number=7,
        created_at=NOW,
    )
    trade = await service_context["service"].set_offer_from_collection_number(
        trade_id=trade.id,
        trainer_id=COUNTERPARTY_ID,
        collection_number=14,
        at=NOW,
    )
    accepted = await service_context["service"].accept_trade(
        trade_id=trade.id,
        trainer_id=INITIATOR_ID,
        at=NOW,
    )

    assert accepted.initiator_accepted_at == NOW
    assert accepted.counterparty_accepted_at is None

    updated = await service_context["service"].set_offer_from_collection_number(
        trade_id=trade.id,
        trainer_id=COUNTERPARTY_ID,
        collection_number=15,
        at=NOW,
    )

    assert updated.counterparty_offer is not None
    assert updated.counterparty_offer.creature_ids == (303,)
    assert updated.initiator_accepted_at is None
    assert updated.counterparty_accepted_at is None


@pytest.mark.asyncio
async def test_set_offer_from_collection_numbers_rejects_missing_collection(
    service_context,
):
    await add_trainers(service_context["trainer_repository"])
    trade = await service_context["service"].create_trade_from_collection_number(
        initiator_trainer_id=INITIATOR_ID,
        counterparty_trainer_id=COUNTERPARTY_ID,
        initiator_collection_number=7,
        created_at=NOW,
    )

    with pytest.raises(TradeCreatureNotFound):
        await service_context["service"].set_offer_from_collection_number(
            trade_id=trade.id,
            trainer_id=COUNTERPARTY_ID,
            collection_number=999,
            at=NOW,
        )


@pytest.mark.asyncio
async def test_set_offer_from_collection_numbers_rejects_multiple_numbers(
    service_context,
):
    await add_trainers(service_context["trainer_repository"])
    trade = await service_context["service"].create_trade_from_collection_number(
        initiator_trainer_id=INITIATOR_ID,
        counterparty_trainer_id=COUNTERPARTY_ID,
        initiator_collection_number=7,
        created_at=NOW,
    )

    with pytest.raises(TradeOfferMustContainExactlyOneCreature):
        await service_context["service"].set_offer_from_collection_numbers(
            trade_id=trade.id,
            trainer_id=COUNTERPARTY_ID,
            collection_numbers=[14, 15],
            at=NOW,
        )


@pytest.mark.asyncio
async def test_first_acceptance_persists_without_executing_trade(service_context):
    await add_trainers(service_context["trainer_repository"])
    trade = await service_context["service"].create_trade_from_collection_number(
        initiator_trainer_id=INITIATOR_ID,
        counterparty_trainer_id=COUNTERPARTY_ID,
        initiator_collection_number=7,
        created_at=NOW,
    )
    await service_context["service"].set_offer_from_collection_number(
        trade_id=trade.id,
        trainer_id=COUNTERPARTY_ID,
        collection_number=14,
        at=NOW,
    )

    accepted = await service_context["service"].accept_trade(
        trade_id=trade.id,
        trainer_id=INITIATOR_ID,
        at=NOW,
    )

    assert accepted.status is TradeStatus.OPEN
    assert accepted.initiator_accepted_at == NOW
    assert service_context["trade_repository"].execute_calls == 0
    assert service_context["initiator_creature"].trainer_id == INITIATOR_ID
    assert service_context["counterparty_creature"].trainer_id == COUNTERPARTY_ID


@pytest.mark.asyncio
async def test_second_acceptance_executes_exchange_and_returns_committed_trade(
    service_context,
):
    await add_trainers(service_context["trainer_repository"])
    initiator_creature = service_context["initiator_creature"]
    counterparty_creature = service_context["counterparty_creature"]
    initiator_snapshot = (
        initiator_creature.id,
        initiator_creature.collection_number,
        initiator_creature.ivs,
        initiator_creature.nature,
        initiator_creature.size,
        initiator_creature.is_shiny,
        initiator_creature.current_form,
    )
    counterparty_snapshot = (
        counterparty_creature.id,
        counterparty_creature.collection_number,
        counterparty_creature.ivs,
        counterparty_creature.nature,
        counterparty_creature.size,
        counterparty_creature.is_shiny,
        counterparty_creature.current_form,
    )

    trade = await service_context["service"].create_trade_from_collection_number(
        initiator_trainer_id=INITIATOR_ID,
        counterparty_trainer_id=COUNTERPARTY_ID,
        initiator_collection_number=7,
        created_at=NOW,
    )
    await service_context["service"].set_offer_from_collection_number(
        trade_id=trade.id,
        trainer_id=COUNTERPARTY_ID,
        collection_number=14,
        at=NOW,
    )
    await service_context["service"].accept_trade(
        trade_id=trade.id,
        trainer_id=INITIATOR_ID,
        at=NOW,
    )

    completed = await service_context["service"].accept_trade(
        trade_id=trade.id,
        trainer_id=COUNTERPARTY_ID,
        at=NOW,
    )

    assert completed.status is TradeStatus.COMPLETED
    assert completed.completed_at == NOW
    assert service_context["trade_repository"].execute_calls == 1
    assert initiator_creature.trainer_id == COUNTERPARTY_ID
    assert counterparty_creature.trainer_id == INITIATOR_ID
    assert initiator_creature.collection_number == counterparty_snapshot[1]
    assert counterparty_creature.collection_number == initiator_snapshot[1]
    assert (
        initiator_creature.id,
        initiator_creature.ivs,
        initiator_creature.nature,
        initiator_creature.size,
        initiator_creature.is_shiny,
        initiator_creature.current_form,
    ) == (
        initiator_snapshot[0],
        initiator_snapshot[2],
        initiator_snapshot[3],
        initiator_snapshot[4],
        initiator_snapshot[5],
        initiator_snapshot[6],
    )
    assert (
        counterparty_creature.id,
        counterparty_creature.ivs,
        counterparty_creature.nature,
        counterparty_creature.size,
        counterparty_creature.is_shiny,
        counterparty_creature.current_form,
    ) == (
        counterparty_snapshot[0],
        counterparty_snapshot[2],
        counterparty_snapshot[3],
        counterparty_snapshot[4],
        counterparty_snapshot[5],
        counterparty_snapshot[6],
    )


@pytest.mark.asyncio
async def test_get_trade_rejects_unknown_trade(service_context):
    with pytest.raises(TradeNotFound):
        await service_context["service"].get_trade(99)
