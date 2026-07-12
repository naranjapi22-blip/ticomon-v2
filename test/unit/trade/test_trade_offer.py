import pytest

from core.trade.exceptions import DuplicateTradeCreature, EmptyTradeOffer
from core.trade.trade_offer import TradeOffer


def test_creates_an_immutable_offer():
    offer = TradeOffer.create(
        trainer_id=10,
        creature_ids=[3, 7],
    )

    assert offer.trainer_id == 10
    assert offer.creature_ids == (3, 7)

    with pytest.raises(AttributeError):
        offer.trainer_id = 20


def test_rejects_empty_offer():
    with pytest.raises(EmptyTradeOffer):
        TradeOffer.create(
            trainer_id=10,
            creature_ids=[],
        )


def test_rejects_duplicate_creature_within_offer():
    with pytest.raises(DuplicateTradeCreature):
        TradeOffer.create(
            trainer_id=10,
            creature_ids=[3, 3],
        )
