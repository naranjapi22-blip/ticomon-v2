import json
from datetime import UTC, date, datetime, timedelta, timezone
from uuid import UUID

import pytest

from core.safari import (
    SafariMapInfluence,
    SafariUnlock,
    SafariUnlockStatus,
    SafariWorld,
)
from infrastructure.safari.unlock_mapper import SafariUnlockMapper
from infrastructure.safari.world_mapper import SafariWorldMapper


def test_world_mapper_round_trip_preserves_state_and_freezes_influence():
    world = SafariWorld(
        guild_id=123,
        current_progress=47,
        daily_unlock_count=2,
        current_influence=SafariMapInfluence({"grass": 4, "poison": 3}),
        last_daily_reset_date=date(2026, 7, 13),
    )

    row_values = SafariWorldMapper.to_row(world)
    restored = SafariWorldMapper.from_row(
        {
            "guild_id": row_values[0],
            "current_progress": row_values[1],
            "daily_unlock_count": row_values[2],
            "current_influence": row_values[3],
            "last_daily_reset_date": row_values[4],
        }
    )

    assert restored.guild_id == world.guild_id
    assert restored.current_progress == world.current_progress
    assert restored.daily_unlock_count == world.daily_unlock_count
    assert dict(restored.current_influence.amounts) == {
        "grass": 4,
        "poison": 3,
    }
    assert restored.last_daily_reset_date == world.last_daily_reset_date

    with pytest.raises(TypeError):
        restored.current_influence.amounts["water"] = 1  # type: ignore[index]


def test_world_mapper_preserves_empty_influence():
    encoded = SafariWorldMapper.encode_influence({})

    assert json.loads(encoded) == {}
    assert SafariWorldMapper._decode_influence(encoded) == {}


@pytest.mark.parametrize(
    "amounts",
    [
        {"Grass": 1},
        {" grass": 1},
        {"grass": -1},
        {"grass": 1.5},
        {"grass": True},
    ],
)
def test_world_mapper_rejects_invalid_persisted_influence(amounts):
    with pytest.raises(ValueError):
        SafariWorldMapper.encode_influence(amounts)


def test_unlock_mapper_round_trip_preserves_available_unlock():
    unlock = SafariUnlock(
        id=7,
        guild_id=123,
        level=3,
        encounter_count=9,
        balls_per_participant=15,
        unlocked_at=datetime(2026, 7, 13, 12, 0, tzinfo=UTC),
        map_influence=SafariMapInfluence({"water": 8}),
    )

    restored = SafariUnlockMapper.from_row(_unlock_row(unlock))

    assert restored.id == 7
    assert restored.guild_id == 123
    assert restored.level == 3
    assert restored.encounter_count == 9
    assert restored.balls_per_participant == 15
    assert restored.unlocked_at == unlock.unlocked_at
    assert restored.status is SafariUnlockStatus.AVAILABLE
    assert dict(restored.map_influence.amounts) == {"water": 8}
    assert restored.consumed_at is None
    assert restored.consumed_session_id is None


def test_unlock_mapper_round_trip_preserves_consumed_unlock():
    consumed_at = datetime(2026, 7, 13, 13, 0, tzinfo=UTC)
    session_id = UUID("11111111-1111-1111-1111-111111111111")
    unlock = SafariUnlock(
        id=8,
        guild_id=123,
        level=1,
        encounter_count=5,
        balls_per_participant=9,
        unlocked_at=datetime(2026, 7, 13, 12, 0, tzinfo=UTC),
        map_influence=SafariMapInfluence(),
        status=SafariUnlockStatus.CONSUMED,
        consumed_at=consumed_at,
        consumed_session_id=session_id,
    )

    restored = SafariUnlockMapper.from_row(_unlock_row(unlock))

    assert restored.status is SafariUnlockStatus.CONSUMED
    assert restored.consumed_at == consumed_at
    assert restored.consumed_session_id == session_id


def test_unlock_mapper_treats_domain_naive_timestamps_as_utc():
    unlock = SafariUnlock(
        id=None,
        guild_id=123,
        level=1,
        encounter_count=5,
        balls_per_participant=9,
        unlocked_at=datetime(2026, 7, 13, 12, 0),
    )

    values = SafariUnlockMapper.to_row(unlock)

    assert values[6] == datetime(2026, 7, 13, 12, 0, tzinfo=UTC)


def test_unlock_mapper_normalizes_aware_timestamps_without_shifting_instant():
    local_time = datetime(
        2026,
        7,
        13,
        6,
        0,
        tzinfo=timezone(timedelta(hours=-6)),
    )

    assert SafariUnlockMapper.as_utc(local_time) == datetime(
        2026,
        7,
        13,
        12,
        0,
        tzinfo=UTC,
    )


def _unlock_row(unlock: SafariUnlock) -> dict:
    values = SafariUnlockMapper.to_row(unlock)
    return {
        "id": unlock.id,
        "guild_id": values[0],
        "level": values[1],
        "encounter_count": values[2],
        "balls_per_participant": values[3],
        "map_influence": values[4],
        "status": values[5],
        "unlocked_at": values[6],
        "consumed_at": values[7],
        "consumed_session_id": values[8],
    }
