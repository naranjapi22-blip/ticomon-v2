import pytest

from core.trade.exceptions import TradeOfferMustContainExactlyOneCreature
from core.trade.trade_offer import TradeOffer


def test_creates_an_immutable_offer():
    offer = TradeOffer.create(
        trainer_id=10,
        creature_id=3,
    )

    assert offer.trainer_id == 10
    assert offer.creature_id == 3
    assert offer.creature_ids == (3,)

    with pytest.raises(AttributeError):
        offer.trainer_id = 20


def test_rejects_missing_creature():
    with pytest.raises(TradeOfferMustContainExactlyOneCreature):
        TradeOffer.create(
            trainer_id=10,
            creature_id=None,  # type: ignore[arg-type]
        )
