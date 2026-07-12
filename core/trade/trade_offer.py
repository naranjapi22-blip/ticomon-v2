from dataclasses import dataclass

from core.trade.exceptions import TradeOfferMustContainExactlyOneCreature


@dataclass(frozen=True, slots=True)
class TradeOffer:
    """A participant's proposed creatures within one trade."""

    trainer_id: int
    creature_ids: tuple[int, ...]

    @classmethod
    def create(
        cls,
        trainer_id: int,
        creature_id: int,
    ) -> "TradeOffer":
        if not isinstance(creature_id, int):
            raise TradeOfferMustContainExactlyOneCreature()

        return cls(
            trainer_id=trainer_id,
            creature_ids=(creature_id,),
        )

    @property
    def creature_id(self) -> int:
        return self.creature_ids[0]
