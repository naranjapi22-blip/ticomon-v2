from core.trade.trade import Trade
from core.trade.trade_offer import TradeOffer
from core.trade.trade_status import TradeStatus


class TradeMapper:
    """Maps persistence records to and from Trade aggregates."""

    @staticmethod
    def from_rows(trade_row, offer_rows) -> Trade:
        offers_by_trainer: dict[int, list[int]] = {}

        for row in offer_rows:
            offers_by_trainer.setdefault(
                row["offering_trainer_id"],
                [],
            ).append(row["creature_id"])

        initiator_id = trade_row["initiator_trainer_id"]
        counterparty_id = trade_row["counterparty_trainer_id"]

        initiator_offer = TradeOffer.create(
            initiator_id,
            offers_by_trainer[initiator_id],
        )
        counterparty_creature_ids = offers_by_trainer.get(counterparty_id)
        counterparty_offer = (
            TradeOffer.create(
                counterparty_id,
                counterparty_creature_ids,
            )
            if counterparty_creature_ids
            else None
        )

        return Trade._reconstitute(
            trade_id=trade_row["id"],
            initiator_trainer_id=initiator_id,
            counterparty_trainer_id=counterparty_id,
            initiator_offer=initiator_offer,
            counterparty_offer=counterparty_offer,
            created_at=trade_row["created_at"],
            expires_at=trade_row["expires_at"],
            status=TradeStatus(trade_row["status"]),
            initiator_accepted_at=trade_row["initiator_accepted_at"],
            counterparty_accepted_at=trade_row["counterparty_accepted_at"],
            cancelled_by_trainer_id=trade_row["cancelled_by_trainer_id"],
            rejected_by_trainer_id=trade_row["rejected_by_trainer_id"],
            completed_at=trade_row["completed_at"],
        )

    @staticmethod
    def to_trade_row(trade: Trade) -> tuple:
        return (
            trade.initiator_trainer_id,
            trade.counterparty_trainer_id,
            trade.status.value,
            trade.initiator_accepted_at,
            trade.counterparty_accepted_at,
            trade.created_at,
            trade.expires_at,
            trade.completed_at,
            trade.cancelled_by_trainer_id,
            trade.rejected_by_trainer_id,
        )

    @staticmethod
    def offers(trade: Trade) -> tuple[TradeOffer, ...]:
        if trade.counterparty_offer is None:
            return (trade.initiator_offer,)

        return (
            trade.initiator_offer,
            trade.counterparty_offer,
        )
