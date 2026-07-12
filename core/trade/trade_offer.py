from dataclasses import dataclass

from core.trade.exceptions import DuplicateTradeCreature, EmptyTradeOffer


@dataclass(frozen=True, slots=True)
class TradeOffer:
    """A participant's proposed creatures within one trade."""

    trainer_id: int
    creature_ids: tuple[int, ...]

    @classmethod
    def create(
        cls,
        trainer_id: int,
        creature_ids: list[int] | tuple[int, ...],
    ) -> "TradeOffer":
        ids = tuple(creature_ids)

        if not ids:
            raise EmptyTradeOffer()

        if len(ids) != len(set(ids)):
            raise DuplicateTradeCreature()

        return cls(
            trainer_id=trainer_id,
            creature_ids=ids,
        )
