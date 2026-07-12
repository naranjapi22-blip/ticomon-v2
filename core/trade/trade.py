from __future__ import annotations

from datetime import datetime

from core.trade.exceptions import (
    DuplicateTradeCreature,
    IncompleteTradeOffer,
    InvalidTradeExpiry,
    InvalidTradeState,
    SameTradeParticipant,
    TradeNotParticipant,
)
from core.trade.trade_offer import TradeOffer
from core.trade.trade_status import TradeStatus


class Trade:
    """Negotiates an exchange of existing creatures between two trainers.

    The aggregate owns the negotiation lifecycle only. It never changes
    creature ownership or marks itself completed; those actions require the
    future repository's atomic persistence operation.
    """

    def __init__(
        self,
        *,
        initiator_trainer_id: int,
        counterparty_trainer_id: int,
        initiator_offer: TradeOffer,
        created_at: datetime,
        expires_at: datetime | None,
    ) -> None:
        self._id: int | None = None
        self._initiator_trainer_id = initiator_trainer_id
        self._counterparty_trainer_id = counterparty_trainer_id
        self._initiator_offer = initiator_offer
        self._counterparty_offer: TradeOffer | None = None
        self._created_at = created_at
        self._expires_at = expires_at
        self._status = TradeStatus.DRAFT
        self._initiator_accepted_at: datetime | None = None
        self._counterparty_accepted_at: datetime | None = None
        self._cancelled_by_trainer_id: int | None = None
        self._rejected_by_trainer_id: int | None = None
        self._completed_at: datetime | None = None

    @classmethod
    def create(
        cls,
        initiator_trainer_id: int,
        counterparty_trainer_id: int,
        initiator_creature_ids: list[int] | tuple[int, ...],
        created_at: datetime,
        expires_at: datetime | None = None,
    ) -> "Trade":
        if initiator_trainer_id == counterparty_trainer_id:
            raise SameTradeParticipant()

        if expires_at is not None and expires_at <= created_at:
            raise InvalidTradeExpiry()

        return cls(
            initiator_trainer_id=initiator_trainer_id,
            counterparty_trainer_id=counterparty_trainer_id,
            initiator_offer=TradeOffer.create(
                initiator_trainer_id,
                initiator_creature_ids,
            ),
            created_at=created_at,
            expires_at=expires_at,
        )

    @classmethod
    def _reconstitute(
        cls,
        *,
        trade_id: int,
        initiator_trainer_id: int,
        counterparty_trainer_id: int,
        initiator_offer: TradeOffer,
        counterparty_offer: TradeOffer | None,
        created_at: datetime,
        expires_at: datetime | None,
        status: TradeStatus,
        initiator_accepted_at: datetime | None,
        counterparty_accepted_at: datetime | None,
        cancelled_by_trainer_id: int | None = None,
        rejected_by_trainer_id: int | None = None,
        completed_at: datetime | None = None,
    ) -> "Trade":
        """Restores a trade from already committed domain state.

        Repository adapters use this factory after loading a persisted record
        or after a successful atomic completion. It is not a lifecycle
        transition and must not be used by application services.
        """

        trade = cls(
            initiator_trainer_id=initiator_trainer_id,
            counterparty_trainer_id=counterparty_trainer_id,
            initiator_offer=initiator_offer,
            created_at=created_at,
            expires_at=expires_at,
        )
        trade._id = trade_id
        trade._counterparty_offer = counterparty_offer
        trade._status = status
        trade._initiator_accepted_at = initiator_accepted_at
        trade._counterparty_accepted_at = counterparty_accepted_at
        trade._cancelled_by_trainer_id = cancelled_by_trainer_id
        trade._rejected_by_trainer_id = rejected_by_trainer_id
        trade._completed_at = completed_at
        return trade

    @property
    def id(self) -> int | None:
        return self._id

    @property
    def initiator_trainer_id(self) -> int:
        return self._initiator_trainer_id

    @property
    def counterparty_trainer_id(self) -> int:
        return self._counterparty_trainer_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def expires_at(self) -> datetime | None:
        return self._expires_at

    @property
    def status(self) -> TradeStatus:
        return self._status

    @property
    def initiator_offer(self) -> TradeOffer:
        return self._initiator_offer

    @property
    def counterparty_offer(self) -> TradeOffer | None:
        return self._counterparty_offer

    @property
    def initiator_accepted_at(self) -> datetime | None:
        return self._initiator_accepted_at

    @property
    def counterparty_accepted_at(self) -> datetime | None:
        return self._counterparty_accepted_at

    @property
    def cancelled_by_trainer_id(self) -> int | None:
        return self._cancelled_by_trainer_id

    @property
    def rejected_by_trainer_id(self) -> int | None:
        return self._rejected_by_trainer_id

    @property
    def completed_at(self) -> datetime | None:
        return self._completed_at

    @property
    def is_terminal(self) -> bool:
        return self._status in {
            TradeStatus.COMPLETED,
            TradeStatus.CANCELLED,
            TradeStatus.REJECTED,
            TradeStatus.EXPIRED,
        }

    @property
    def is_fully_accepted(self) -> bool:
        return (
            self._initiator_accepted_at is not None
            and self._counterparty_accepted_at is not None
        )

    @property
    def is_ready_to_execute(self) -> bool:
        return self._status is TradeStatus.OPEN and self.is_fully_accepted

    def offer_for(self, participant_id: int) -> TradeOffer | None:
        self._ensure_participant(participant_id)

        if participant_id == self._initiator_trainer_id:
            return self._initiator_offer

        return self._counterparty_offer

    def set_offer(
        self,
        actor_trainer_id: int,
        creature_ids: list[int] | tuple[int, ...],
        at: datetime,
    ) -> None:
        self._ensure_mutable(at)
        self._ensure_participant(actor_trainer_id)

        offer = TradeOffer.create(
            actor_trainer_id,
            creature_ids,
        )

        other_offer = (
            self._counterparty_offer
            if actor_trainer_id == self._initiator_trainer_id
            else self._initiator_offer
        )

        if other_offer is not None and set(offer.creature_ids) & set(
            other_offer.creature_ids
        ):
            raise DuplicateTradeCreature()

        if self.offer_for(actor_trainer_id) == offer:
            return

        if actor_trainer_id == self._initiator_trainer_id:
            self._initiator_offer = offer
        else:
            self._counterparty_offer = offer

        self._clear_acceptances()
        self._status = (
            TradeStatus.OPEN
            if self._counterparty_offer is not None
            else TradeStatus.DRAFT
        )

    def accept(
        self,
        actor_trainer_id: int,
        at: datetime,
    ) -> None:
        self._ensure_mutable(at)
        self._ensure_participant(actor_trainer_id)

        if self._status is not TradeStatus.OPEN:
            raise IncompleteTradeOffer()

        if actor_trainer_id == self._initiator_trainer_id:
            if self._initiator_accepted_at is None:
                self._initiator_accepted_at = at
            return

        if self._counterparty_accepted_at is None:
            self._counterparty_accepted_at = at

    def cancel(
        self,
        actor_trainer_id: int,
        at: datetime,
    ) -> None:
        self._ensure_mutable(at)
        self._ensure_participant(actor_trainer_id)

        self._status = TradeStatus.CANCELLED
        self._cancelled_by_trainer_id = actor_trainer_id

    def reject(
        self,
        actor_trainer_id: int,
        at: datetime,
    ) -> None:
        self._ensure_mutable(at)

        if actor_trainer_id != self._counterparty_trainer_id:
            raise TradeNotParticipant()

        self._status = TradeStatus.REJECTED
        self._rejected_by_trainer_id = actor_trainer_id

    def expire(self, at: datetime) -> bool:
        if self.is_terminal or not self._is_expired_at(at):
            return False

        self._status = TradeStatus.EXPIRED
        return True

    def assert_ready_to_execute(self, at: datetime) -> None:
        """Verifies the negotiation may enter atomic repository execution.

        This method intentionally does not mutate the aggregate. Only a
        successful repository transaction may persist a completed trade.
        """

        if self._is_expired_at(at) or not self.is_ready_to_execute:
            raise InvalidTradeState()

    def _ensure_mutable(self, at: datetime) -> None:
        self.expire(at)

        if self.is_terminal:
            raise InvalidTradeState()

    def _ensure_participant(self, trainer_id: int) -> None:
        if trainer_id not in {
            self._initiator_trainer_id,
            self._counterparty_trainer_id,
        }:
            raise TradeNotParticipant()

    def _is_expired_at(self, at: datetime) -> bool:
        return self._expires_at is not None and at >= self._expires_at

    def _clear_acceptances(self) -> None:
        self._initiator_accepted_at = None
        self._counterparty_accepted_at = None
