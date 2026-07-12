from datetime import datetime, timedelta

import pytest

from core.trade.exceptions import (
    DuplicateTradeCreature,
    IncompleteTradeOffer,
    InvalidTradeExpiry,
    InvalidTradeState,
    SameTradeParticipant,
    TradeNotParticipant,
)
from core.trade.trade import Trade
from core.trade.trade_status import TradeStatus

NOW = datetime(2026, 7, 12, 12, 0, 0)
INITIATOR_ID = 10
COUNTERPARTY_ID = 20


def create_trade(**overrides) -> Trade:
    values = {
        "initiator_trainer_id": INITIATOR_ID,
        "counterparty_trainer_id": COUNTERPARTY_ID,
        "initiator_creature_ids": [101],
        "created_at": NOW,
    }
    values.update(overrides)
    return Trade.create(**values)


def open_trade() -> Trade:
    trade = create_trade()
    trade.set_offer(
        actor_trainer_id=COUNTERPARTY_ID,
        creature_ids=[202],
        at=NOW,
    )
    return trade


def test_creates_draft_with_private_read_only_state():
    trade = create_trade()

    assert trade.id is None
    assert trade.status is TradeStatus.DRAFT
    assert trade.initiator_offer.creature_ids == (101,)
    assert trade.counterparty_offer is None
    assert not trade.is_ready_to_execute

    with pytest.raises(AttributeError):
        trade.status = TradeStatus.OPEN


def test_rejects_same_trainer_as_both_participants():
    with pytest.raises(SameTradeParticipant):
        create_trade(counterparty_trainer_id=INITIATOR_ID)


def test_rejects_expiry_at_or_before_creation():
    with pytest.raises(InvalidTradeExpiry):
        create_trade(expires_at=NOW)


def test_counterparty_offer_opens_trade():
    trade = open_trade()

    assert trade.status is TradeStatus.OPEN
    assert trade.counterparty_offer is not None
    assert trade.counterparty_offer.creature_ids == (202,)


def test_offer_for_rejects_non_participant():
    trade = create_trade()

    with pytest.raises(TradeNotParticipant):
        trade.offer_for(999)


def test_offer_for_returns_none_when_counterparty_has_not_offered():
    trade = create_trade()

    assert trade.offer_for(COUNTERPARTY_ID) is None


def test_rejects_creature_present_in_both_offers():
    trade = create_trade()

    with pytest.raises(DuplicateTradeCreature):
        trade.set_offer(
            actor_trainer_id=COUNTERPARTY_ID,
            creature_ids=[101],
            at=NOW,
        )


def test_acceptance_requires_both_offers():
    trade = create_trade()

    with pytest.raises(IncompleteTradeOffer):
        trade.accept(
            actor_trainer_id=INITIATOR_ID,
            at=NOW,
        )


def test_both_participants_must_accept_before_execution():
    trade = open_trade()

    trade.accept(INITIATOR_ID, NOW)

    assert not trade.is_fully_accepted
    assert not trade.is_ready_to_execute

    trade.accept(COUNTERPARTY_ID, NOW)

    assert trade.is_fully_accepted
    assert trade.is_ready_to_execute


def test_changing_offer_clears_both_acceptances():
    trade = open_trade()
    trade.accept(INITIATOR_ID, NOW)
    trade.accept(COUNTERPARTY_ID, NOW)

    trade.set_offer(
        actor_trainer_id=COUNTERPARTY_ID,
        creature_ids=[203],
        at=NOW,
    )

    assert trade.status is TradeStatus.OPEN
    assert trade.initiator_accepted_at is None
    assert trade.counterparty_accepted_at is None
    assert not trade.is_ready_to_execute


def test_setting_the_same_offer_does_not_clear_existing_acceptance():
    trade = open_trade()
    trade.accept(INITIATOR_ID, NOW)

    trade.set_offer(
        actor_trainer_id=COUNTERPARTY_ID,
        creature_ids=[202],
        at=NOW,
    )

    assert trade.initiator_accepted_at == NOW


def test_only_participants_can_accept_or_cancel():
    trade = open_trade()

    with pytest.raises(TradeNotParticipant):
        trade.accept(999, NOW)

    with pytest.raises(TradeNotParticipant):
        trade.cancel(999, NOW)


def test_only_counterparty_can_reject():
    trade = create_trade()

    with pytest.raises(TradeNotParticipant):
        trade.reject(INITIATOR_ID, NOW)

    trade.reject(COUNTERPARTY_ID, NOW)

    assert trade.status is TradeStatus.REJECTED
    assert trade.rejected_by_trainer_id == COUNTERPARTY_ID


def test_cancelled_trade_is_terminal():
    trade = create_trade()
    trade.cancel(INITIATOR_ID, NOW)

    assert trade.status is TradeStatus.CANCELLED
    assert trade.cancelled_by_trainer_id == INITIATOR_ID

    with pytest.raises(InvalidTradeState):
        trade.set_offer(COUNTERPARTY_ID, [202], NOW)


def test_expire_transitions_an_active_trade_to_expired():
    trade = create_trade(expires_at=NOW + timedelta(minutes=5))

    assert not trade.expire(NOW + timedelta(minutes=4))
    assert trade.status is TradeStatus.DRAFT

    assert trade.expire(NOW + timedelta(minutes=5))
    assert trade.status is TradeStatus.EXPIRED


def test_assert_ready_to_execute_requires_both_acceptances():
    trade = open_trade()

    with pytest.raises(InvalidTradeState):
        trade.assert_ready_to_execute(NOW)

    trade.accept(INITIATOR_ID, NOW)
    trade.accept(COUNTERPARTY_ID, NOW)
    trade.assert_ready_to_execute(NOW)


def test_assert_ready_to_execute_does_not_complete_trade():
    trade = open_trade()
    trade.accept(INITIATOR_ID, NOW)
    trade.accept(COUNTERPARTY_ID, NOW)

    trade.assert_ready_to_execute(NOW)

    assert trade.status is TradeStatus.OPEN
    assert not hasattr(trade, "mark_completed")


def test_assert_ready_to_execute_rejects_an_expired_trade_without_mutation():
    trade = create_trade(expires_at=NOW + timedelta(minutes=5))
    trade.set_offer(COUNTERPARTY_ID, [202], NOW)
    trade.accept(INITIATOR_ID, NOW)
    trade.accept(COUNTERPARTY_ID, NOW)

    with pytest.raises(InvalidTradeState):
        trade.assert_ready_to_execute(NOW + timedelta(minutes=5))

    assert trade.status is TradeStatus.OPEN
