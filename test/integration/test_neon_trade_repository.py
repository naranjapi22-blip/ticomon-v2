import asyncio
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio

from core.trade.exceptions import TradeExecutionConflict
from core.trade.trade import Trade
from core.trade.trade_status import TradeStatus
from infrastructure.db_config import get_pool
from infrastructure.persistence.repositories.neon_trade_repository import (
    NeonTradeRepository,
)
from scripts.create_trade_schema import create_trade_schema

NOW = datetime(2026, 7, 12, 12, 0, 0, tzinfo=UTC)


@pytest_asyncio.fixture
async def trade_data_factory():
    await create_trade_schema()
    pool = await get_pool()
    created_creature_ids: list[int] = []
    participant_ids: list[int] = []

    async def create(
        *,
        same_collection_number: bool = False,
    ):
        initiator_id = uuid.uuid4().int & 0x7FFFFFFFFFFFFFFF
        counterparty_id = uuid.uuid4().int & 0x7FFFFFFFFFFFFFFF
        participant_ids.extend(
            [
                initiator_id,
                counterparty_id,
            ]
        )

        async with pool.acquire() as connection:
            initiator_creature_id = await _insert_creature(
                connection,
                trainer_id=initiator_id,
                collection_number=7,
                is_shiny=True,
            )
            counterparty_creature_id = await _insert_creature(
                connection,
                trainer_id=counterparty_id,
                collection_number=(7 if same_collection_number else 14),
                is_shiny=False,
            )
            created_creature_ids.extend(
                [
                    initiator_creature_id,
                    counterparty_creature_id,
                ]
            )

        return {
            "initiator_id": initiator_id,
            "counterparty_id": counterparty_id,
            "initiator_creature_id": initiator_creature_id,
            "counterparty_creature_id": counterparty_creature_id,
        }

    yield create

    async with pool.acquire() as connection:
        if participant_ids:
            await connection.execute(
                """
                DELETE FROM trades
                WHERE initiator_trainer_id = ANY($1::bigint[])
                   OR counterparty_trainer_id = ANY($1::bigint[])
                """,
                participant_ids,
            )

        if created_creature_ids:
            await connection.execute(
                """
                DELETE FROM creatures
                WHERE id = ANY($1::bigint[])
                """,
                created_creature_ids,
            )


@pytest.mark.asyncio
async def test_saves_and_reloads_trade_with_offers(trade_data_factory):
    data = await trade_data_factory()
    repository = NeonTradeRepository()

    trade = await _create_open_trade(repository, data)
    reloaded = await repository.get(trade.id)

    assert reloaded is not None
    assert reloaded.id == trade.id
    assert reloaded.status is TradeStatus.OPEN
    assert reloaded.initiator_offer.creature_ids == (data["initiator_creature_id"],)
    assert reloaded.counterparty_offer is not None
    assert reloaded.counterparty_offer.creature_ids == (
        data["counterparty_creature_id"],
    )
    assert reloaded.created_at.tzinfo is UTC
    assert reloaded.created_at.utcoffset().total_seconds() == 0


@pytest.mark.asyncio
async def test_executes_atomic_trade_and_swaps_collection_numbers(
    trade_data_factory,
):
    data = await trade_data_factory()
    repository = NeonTradeRepository()
    trade = await _create_ready_trade(repository, data)
    pool = await get_pool()

    async with pool.acquire() as connection:
        before_rows = await connection.fetch(
            """
            SELECT *
            FROM creatures
            WHERE id = ANY($1::bigint[])
            ORDER BY id
            """,
            sorted(
                [
                    data["initiator_creature_id"],
                    data["counterparty_creature_id"],
                ]
            ),
        )

    completed = await repository.execute_completed_trade(
        trade,
        completed_at=NOW,
    )

    async with pool.acquire() as connection:
        after_rows = await connection.fetch(
            """
            SELECT *
            FROM creatures
            WHERE id = ANY($1::bigint[])
            ORDER BY id
            """,
            sorted(
                [
                    data["initiator_creature_id"],
                    data["counterparty_creature_id"],
                ]
            ),
        )

    assert completed.status is TradeStatus.COMPLETED
    assert completed.completed_at == NOW
    assert completed.completed_at.tzinfo is UTC

    expected_owner = {
        data["initiator_creature_id"]: data["counterparty_id"],
        data["counterparty_creature_id"]: data["initiator_id"],
    }
    expected_collection_number = {
        data["initiator_creature_id"]: before_rows[1]["collection_number"],
        data["counterparty_creature_id"]: before_rows[0]["collection_number"],
    }

    for before, after in zip(before_rows, after_rows, strict=True):
        assert after["trainer_id"] == expected_owner[after["id"]]
        assert after["collection_number"] == expected_collection_number[after["id"]]

        for field in (
            "id",
            "species_id",
            "current_form_id",
            "is_shiny",
            "nature",
            "size",
            "hp_iv",
            "attack_iv",
            "defense_iv",
            "special_attack_iv",
            "special_defense_iv",
            "speed_iv",
        ):
            assert after[field] == before[field]


@pytest.mark.asyncio
async def test_rolls_back_when_live_ownership_changed(trade_data_factory):
    data = await trade_data_factory()
    repository = NeonTradeRepository()
    trade = await _create_ready_trade(repository, data)
    pool = await get_pool()
    third_trainer_id = uuid.uuid4().int & 0x7FFFFFFFFFFFFFFF

    async with pool.acquire() as connection:
        await connection.execute(
            """
            UPDATE creatures
            SET trainer_id = $1
            WHERE id = $2
            """,
            third_trainer_id,
            data["initiator_creature_id"],
        )

    with pytest.raises(TradeExecutionConflict):
        await repository.execute_completed_trade(
            trade,
            completed_at=NOW,
        )

    async with pool.acquire() as connection:
        counterparty_owner = await connection.fetchval(
            """
            SELECT trainer_id
            FROM creatures
            WHERE id = $1
            """,
            data["counterparty_creature_id"],
        )
        status = await connection.fetchval(
            """
            SELECT status
            FROM trades
            WHERE id = $1
            """,
            trade.id,
        )

    assert counterparty_owner == data["counterparty_id"]
    assert status == TradeStatus.OPEN.value


@pytest.mark.asyncio
async def test_rolls_back_on_stale_collection_number_snapshot(trade_data_factory):
    data = await trade_data_factory()
    repository = NeonTradeRepository()
    trade = await _create_ready_trade(repository, data)
    pool = await get_pool()

    async with pool.acquire() as connection:
        await connection.execute(
            """
            UPDATE creatures
            SET collection_number = $1
            WHERE id = $2
            """,
            99,
            data["initiator_creature_id"],
        )

    with pytest.raises(TradeExecutionConflict):
        await repository.execute_completed_trade(
            trade,
            completed_at=NOW,
        )

    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT id, trainer_id, collection_number
            FROM creatures
            WHERE id = ANY($1::bigint[])
            ORDER BY id
            """,
            [
                data["initiator_creature_id"],
                data["counterparty_creature_id"],
            ],
        )
        status = await connection.fetchval(
            """
            SELECT status
            FROM trades
            WHERE id = $1
            """,
            trade.id,
        )

    rows_by_id = {row["id"]: row for row in rows}
    assert (
        rows_by_id[data["initiator_creature_id"]]["trainer_id"] == data["initiator_id"]
    )
    assert rows_by_id[data["initiator_creature_id"]]["collection_number"] == 99
    assert (
        rows_by_id[data["counterparty_creature_id"]]["trainer_id"]
        == data["counterparty_id"]
    )
    assert rows_by_id[data["counterparty_creature_id"]]["collection_number"] == 14
    assert status == TradeStatus.OPEN.value


@pytest.mark.asyncio
async def test_allows_reciprocal_swap_of_same_collection_number(
    trade_data_factory,
):
    data = await trade_data_factory(same_collection_number=True)
    repository = NeonTradeRepository()
    trade = await _create_ready_trade(repository, data)
    pool = await get_pool()

    completed = await repository.execute_completed_trade(
        trade,
        completed_at=NOW,
    )

    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT id, trainer_id, collection_number
            FROM creatures
            WHERE id = ANY($1::bigint[])
            ORDER BY id
            """,
            [
                data["initiator_creature_id"],
                data["counterparty_creature_id"],
            ],
        )

    owners = {row["id"]: row["trainer_id"] for row in rows}
    assert completed.status is TradeStatus.COMPLETED
    assert owners[data["initiator_creature_id"]] == data["counterparty_id"]
    assert owners[data["counterparty_creature_id"]] == data["initiator_id"]
    assert {row["collection_number"] for row in rows} == {7}


@pytest.mark.asyncio
async def test_trade_row_lock_allows_exactly_one_concurrent_completion(
    trade_data_factory,
):
    data = await trade_data_factory()
    repository = NeonTradeRepository()
    trade = await _create_ready_trade(repository, data)

    results = await asyncio.gather(
        repository.execute_completed_trade(trade, completed_at=NOW),
        repository.execute_completed_trade(trade, completed_at=NOW),
        return_exceptions=True,
    )

    completed = [result for result in results if isinstance(result, Trade)]
    conflicts = [
        result for result in results if isinstance(result, TradeExecutionConflict)
    ]

    assert len(completed) == 1
    assert completed[0].status is TradeStatus.COMPLETED
    assert len(conflicts) == 1


async def _create_open_trade(repository, data) -> Trade:
    trade = Trade.create(
        initiator_trainer_id=data["initiator_id"],
        counterparty_trainer_id=data["counterparty_id"],
        initiator_creature_id=data["initiator_creature_id"],
        created_at=NOW,
    )
    trade = await repository.save(trade)
    trade.set_offer(
        actor_trainer_id=data["counterparty_id"],
        creature_id=data["counterparty_creature_id"],
        at=NOW,
    )
    return await repository.save(trade)


async def _create_ready_trade(repository, data) -> Trade:
    trade = await _create_open_trade(repository, data)
    trade.accept(data["initiator_id"], NOW)
    trade = await repository.save(trade)
    trade.accept(data["counterparty_id"], NOW)
    return trade


async def _insert_creature(
    connection,
    *,
    trainer_id: int,
    collection_number: int,
    is_shiny: bool,
) -> int:
    return await connection.fetchval(
        """
        INSERT INTO creatures (
            trainer_id,
            collection_number,
            species_id,
            current_form_id,
            is_shiny,
            nature,
            size,
            hp_iv,
            attack_iv,
            defense_iv,
            special_attack_iv,
            special_defense_iv,
            speed_iv
        )
        VALUES (
            $1, $2, 1, NULL, $3, 'hardy', 1.0,
            31, 30, 29, 28, 27, 26
        )
        RETURNING id
        """,
        trainer_id,
        collection_number,
        is_shiny,
    )
