from datetime import datetime

import asyncpg

from core.trade.exceptions import TradeExecutionConflict
from core.trade.trade import Trade
from core.trade.trade_repository import TradeRepository
from core.trade.trade_status import TradeStatus
from infrastructure.db_config import get_pool
from infrastructure.persistence.mappers.trade_mapper import TradeMapper


class NeonTradeRepository(TradeRepository):
    """PostgreSQL implementation of the Trade persistence boundary."""

    def __init__(self) -> None:
        self._mapper = TradeMapper()

    async def save(self, trade: Trade) -> Trade:
        pool = await get_pool()

        async with pool.acquire() as connection:
            async with connection.transaction():
                existing_offer_rows = []

                if trade.id is None:
                    trade_row = await connection.fetchrow(
                        """
                        INSERT INTO trades (
                            initiator_trainer_id,
                            counterparty_trainer_id,
                            status,
                            initiator_accepted_at,
                            counterparty_accepted_at,
                            created_at,
                            expires_at,
                            completed_at,
                            cancelled_by_trainer_id,
                            rejected_by_trainer_id
                        )
                        VALUES (
                            $1, $2, $3, $4, $5,
                            $6, $7, $8, $9, $10
                        )
                        RETURNING *
                        """,
                        *self._mapper.to_trade_row(trade),
                    )
                else:
                    locked = await connection.fetchrow(
                        """
                        SELECT id
                        FROM trades
                        WHERE id = $1
                        FOR UPDATE
                        """,
                        trade.id,
                    )

                    if locked is None:
                        raise ValueError(f"Trade {trade.id} was not found.")

                    existing_offer_rows = await self._lock_offer_rows(
                        connection,
                        trade.id,
                    )
                    trade_row = await connection.fetchrow(
                        """
                        UPDATE trades
                        SET
                            initiator_trainer_id = $1,
                            counterparty_trainer_id = $2,
                            status = $3,
                            initiator_accepted_at = $4,
                            counterparty_accepted_at = $5,
                            created_at = $6,
                            expires_at = $7,
                            completed_at = $8,
                            cancelled_by_trainer_id = $9,
                            rejected_by_trainer_id = $10
                        WHERE id = $11
                        RETURNING *
                        """,
                        *self._mapper.to_trade_row(trade),
                        trade.id,
                    )

                assert trade_row is not None
                trade_id = trade_row["id"]

                if self._offer_signature(existing_offer_rows) != (
                    self._trade_offer_signature(trade)
                ):
                    await self._replace_offer_rows(
                        connection,
                        trade_id,
                        trade,
                    )

                offer_rows = await self._fetch_offer_rows(
                    connection,
                    trade_id,
                )

        return self._mapper.from_rows(
            trade_row,
            offer_rows,
        )

    async def get(self, trade_id: int) -> Trade | None:
        pool = await get_pool()

        async with pool.acquire() as connection:
            trade_row = await connection.fetchrow(
                """
                SELECT *
                FROM trades
                WHERE id = $1
                """,
                trade_id,
            )

            if trade_row is None:
                return None

            offer_rows = await self._fetch_offer_rows(
                connection,
                trade_id,
            )

        return self._mapper.from_rows(
            trade_row,
            offer_rows,
        )

    async def execute_completed_trade(
        self,
        trade: Trade,
        completed_at: datetime,
    ) -> Trade:
        trade.assert_ready_to_execute(completed_at)

        if trade.id is None:
            raise TradeExecutionConflict()

        pool = await get_pool()

        try:
            async with pool.acquire() as connection:
                async with connection.transaction():
                    trade_row = await connection.fetchrow(
                        """
                        SELECT *
                        FROM trades
                        WHERE id = $1
                        FOR UPDATE
                        """,
                        trade.id,
                    )

                    if trade_row is None:
                        raise TradeExecutionConflict()

                    offer_rows = await self._lock_offer_rows(
                        connection,
                        trade.id,
                    )
                    self._validate_persisted_trade(
                        trade,
                        trade_row,
                        offer_rows,
                        completed_at,
                    )

                    creature_rows = await self._lock_relevant_creatures(
                        connection,
                        trade,
                        offer_rows,
                    )
                    self._validate_creatures(
                        trade,
                        offer_rows,
                        creature_rows,
                    )

                    await connection.execute(
                        """
                        SET CONSTRAINTS
                            creatures_trainer_collection_number_unique
                        DEFERRED
                        """
                    )

                    initiator_ids = list(
                        trade.initiator_offer.creature_ids,
                    )
                    assert trade.counterparty_offer is not None
                    counterparty_ids = list(
                        trade.counterparty_offer.creature_ids,
                    )
                    all_ids = sorted(
                        [
                            *initiator_ids,
                            *counterparty_ids,
                        ]
                    )
                    updated_creatures = await connection.fetch(
                        """
                        UPDATE creatures
                        SET trainer_id = CASE
                            WHEN id = ANY($1::bigint[]) THEN $2
                            WHEN id = ANY($3::bigint[]) THEN $4
                            ELSE trainer_id
                        END
                        WHERE id = ANY($5::bigint[])
                        RETURNING id
                        """,
                        initiator_ids,
                        trade.counterparty_trainer_id,
                        counterparty_ids,
                        trade.initiator_trainer_id,
                        all_ids,
                    )

                    if len(updated_creatures) != len(all_ids):
                        raise TradeExecutionConflict()

                    completed_row = await connection.fetchrow(
                        """
                        UPDATE trades
                        SET
                            status = $1,
                            initiator_accepted_at = $2,
                            counterparty_accepted_at = $3,
                            completed_at = $4
                        WHERE id = $5
                        RETURNING *
                        """,
                        TradeStatus.COMPLETED.value,
                        trade.initiator_accepted_at,
                        trade.counterparty_accepted_at,
                        completed_at,
                        trade.id,
                    )

                    if completed_row is None:
                        raise TradeExecutionConflict()

                    completed_trade = self._mapper.from_rows(
                        completed_row,
                        offer_rows,
                    )

        except asyncpg.UniqueViolationError as error:
            raise TradeExecutionConflict() from error

        return completed_trade

    async def _replace_offer_rows(
        self,
        connection,
        trade_id: int,
        trade: Trade,
    ) -> None:
        offers = self._mapper.offers(trade)
        creature_ids = sorted(
            creature_id for offer in offers for creature_id in offer.creature_ids
        )
        creature_rows = await connection.fetch(
            """
            SELECT id, trainer_id, collection_number
            FROM creatures
            WHERE id = ANY($1::bigint[])
            ORDER BY id
            FOR SHARE
            """,
            creature_ids,
        )

        if len(creature_rows) != len(creature_ids):
            raise TradeExecutionConflict()

        creatures_by_id = {row["id"]: row for row in creature_rows}
        values = []

        for offer in offers:
            for creature_id in offer.creature_ids:
                creature_row = creatures_by_id[creature_id]

                if creature_row["trainer_id"] != offer.trainer_id:
                    raise TradeExecutionConflict()

                values.append(
                    (
                        trade_id,
                        offer.trainer_id,
                        creature_id,
                        creature_row["collection_number"],
                    )
                )

        await connection.execute(
            """
            DELETE FROM trade_offer_items
            WHERE trade_id = $1
            """,
            trade_id,
        )
        await connection.executemany(
            """
            INSERT INTO trade_offer_items (
                trade_id,
                offering_trainer_id,
                creature_id,
                collection_number_at_offer
            )
            VALUES ($1, $2, $3, $4)
            """,
            values,
        )

    async def _lock_relevant_creatures(
        self,
        connection,
        trade: Trade,
        offer_rows,
    ):
        offered_ids = sorted(row["creature_id"] for row in offer_rows)
        incoming_trainer_ids = []
        incoming_collection_numbers = []

        for row in offer_rows:
            target_trainer_id = self._target_trainer_id(
                trade,
                row["offering_trainer_id"],
            )
            incoming_trainer_ids.append(target_trainer_id)
            incoming_collection_numbers.append(
                row["collection_number_at_offer"],
            )

        return await connection.fetch(
            """
            WITH incoming(trainer_id, collection_number) AS (
                SELECT *
                FROM unnest($2::bigint[], $3::integer[])
            )
            SELECT c.id, c.trainer_id, c.collection_number
            FROM creatures c
            WHERE c.id = ANY($1::bigint[])
               OR EXISTS (
                    SELECT 1
                    FROM incoming i
                    WHERE i.trainer_id = c.trainer_id
                      AND i.collection_number = c.collection_number
               )
            ORDER BY c.id
            FOR UPDATE
            """,
            offered_ids,
            incoming_trainer_ids,
            incoming_collection_numbers,
        )

    @staticmethod
    def _validate_persisted_trade(
        trade: Trade,
        trade_row,
        offer_rows,
        completed_at: datetime,
    ) -> None:
        if trade_row["status"] != TradeStatus.OPEN.value:
            raise TradeExecutionConflict()

        if (
            trade_row["initiator_trainer_id"] != trade.initiator_trainer_id
            or trade_row["counterparty_trainer_id"] != trade.counterparty_trainer_id
            or trade_row["created_at"] != trade.created_at
            or trade_row["expires_at"] != trade.expires_at
        ):
            raise TradeExecutionConflict()

        if (
            trade_row["expires_at"] is not None
            and completed_at >= trade_row["expires_at"]
        ):
            raise TradeExecutionConflict()

        persisted_acceptances = (
            trade_row["initiator_accepted_at"],
            trade_row["counterparty_accepted_at"],
        )
        requested_acceptances = (
            trade.initiator_accepted_at,
            trade.counterparty_accepted_at,
        )

        for persisted, requested in zip(
            persisted_acceptances,
            requested_acceptances,
            strict=True,
        ):
            if requested is None or (persisted is not None and persisted != requested):
                raise TradeExecutionConflict()

        if NeonTradeRepository._offer_signature(offer_rows) != (
            NeonTradeRepository._trade_offer_signature(trade)
        ):
            raise TradeExecutionConflict()

    @staticmethod
    def _validate_creatures(
        trade: Trade,
        offer_rows,
        creature_rows,
    ) -> None:
        offered_ids = {row["creature_id"] for row in offer_rows}
        creatures_by_id = {row["id"]: row for row in creature_rows}

        if not offered_ids.issubset(creatures_by_id):
            raise TradeExecutionConflict()

        outgoing_by_trainer: dict[int, set[int]] = {}
        incoming_pairs: set[tuple[int, int]] = set()

        for offer_row in offer_rows:
            creature = creatures_by_id[offer_row["creature_id"]]

            if (
                creature["trainer_id"] != offer_row["offering_trainer_id"]
                or creature["collection_number"]
                != offer_row["collection_number_at_offer"]
            ):
                raise TradeExecutionConflict()

            outgoing_by_trainer.setdefault(
                offer_row["offering_trainer_id"],
                set(),
            ).add(offer_row["creature_id"])
            incoming_pair = (
                NeonTradeRepository._target_trainer_id(
                    trade,
                    offer_row["offering_trainer_id"],
                ),
                offer_row["collection_number_at_offer"],
            )

            if incoming_pair in incoming_pairs:
                raise TradeExecutionConflict()

            incoming_pairs.add(incoming_pair)

        for creature in creature_rows:
            pair = (
                creature["trainer_id"],
                creature["collection_number"],
            )

            if pair not in incoming_pairs:
                continue

            outgoing_ids = outgoing_by_trainer.get(
                creature["trainer_id"],
                set(),
            )

            if creature["id"] not in outgoing_ids:
                raise TradeExecutionConflict()

    @staticmethod
    async def _fetch_offer_rows(connection, trade_id: int):
        return await connection.fetch(
            """
            SELECT *
            FROM trade_offer_items
            WHERE trade_id = $1
            ORDER BY creature_id
            """,
            trade_id,
        )

    @staticmethod
    async def _lock_offer_rows(connection, trade_id: int):
        return await connection.fetch(
            """
            SELECT *
            FROM trade_offer_items
            WHERE trade_id = $1
            ORDER BY creature_id
            FOR UPDATE
            """,
            trade_id,
        )

    @staticmethod
    def _target_trainer_id(
        trade: Trade,
        offering_trainer_id: int,
    ) -> int:
        if offering_trainer_id == trade.initiator_trainer_id:
            return trade.counterparty_trainer_id

        if offering_trainer_id == trade.counterparty_trainer_id:
            return trade.initiator_trainer_id

        raise TradeExecutionConflict()

    @staticmethod
    def _offer_signature(offer_rows) -> set[tuple[int, int]]:
        return {
            (
                row["offering_trainer_id"],
                row["creature_id"],
            )
            for row in offer_rows
        }

    @staticmethod
    def _trade_offer_signature(trade: Trade) -> set[tuple[int, int]]:
        return {
            (
                offer.trainer_id,
                creature_id,
            )
            for offer in TradeMapper.offers(trade)
            for creature_id in offer.creature_ids
        }
