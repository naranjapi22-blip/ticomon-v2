from datetime import UTC, datetime

import pytest

from application.battle.battle_application_service import BattleApplicationService
from application.battle.exceptions import BattleCreatureNotOnTeam
from core.battle.exceptions import InsufficientTeamSize, SameBattleParticipant
from core.team.team_slot import TeamSlot
from test.builders.creature_builder import CreatureBuilder
from test.fakes.fake_battle_repository import FakeBattleRepository
from test.fakes.fake_creature_repository import FakeCreatureRepository
from test.fakes.fake_team_repository import FakeTeamRepository

INITIATOR_ID = 1
OPPONENT_ID = 2


@pytest.fixture
def battle_context():
    creatures = [
        CreatureBuilder()
        .with_id(101)
        .with_trainer_id(INITIATOR_ID)
        .with_collection_number(1)
        .build(),
        CreatureBuilder()
        .with_id(102)
        .with_trainer_id(INITIATOR_ID)
        .with_collection_number(2)
        .build(),
        CreatureBuilder()
        .with_id(103)
        .with_trainer_id(INITIATOR_ID)
        .with_collection_number(3)
        .build(),
        CreatureBuilder()
        .with_id(201)
        .with_trainer_id(OPPONENT_ID)
        .with_collection_number(4)
        .build(),
        CreatureBuilder()
        .with_id(202)
        .with_trainer_id(OPPONENT_ID)
        .with_collection_number(5)
        .build(),
        CreatureBuilder()
        .with_id(203)
        .with_trainer_id(OPPONENT_ID)
        .with_collection_number(6)
        .build(),
    ]

    creature_repository = FakeCreatureRepository(*creatures)
    team_repository = FakeTeamRepository()
    battle_repository = FakeBattleRepository()

    for slot, creature in enumerate(creatures[:3], start=1):
        team_repository._slots[(INITIATOR_ID, slot)] = TeamSlot(
            id=slot,
            trainer_id=INITIATOR_ID,
            slot=slot,
            creature_id=creature.id,
        )

    for slot, creature in enumerate(creatures[3:], start=1):
        team_repository._slots[(OPPONENT_ID, slot)] = TeamSlot(
            id=slot + 10,
            trainer_id=OPPONENT_ID,
            slot=slot,
            creature_id=creature.id,
        )

    service = BattleApplicationService(
        battle_repository=battle_repository,
        team_repository=team_repository,
        creature_repository=creature_repository,
    )

    return {
        "service": service,
        "team_repository": team_repository,
    }


@pytest.mark.asyncio
async def test_create_challenge_requires_three_team_members(battle_context):
    service = battle_context["service"]
    team_repository = battle_context["team_repository"]

    team_repository._slots.pop((OPPONENT_ID, 3), None)

    with pytest.raises(InsufficientTeamSize):
        await service.create_challenge(
            initiator_trainer_id=INITIATOR_ID,
            opponent_trainer_id=OPPONENT_ID,
            created_at=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_create_challenge_rejects_self_battle(battle_context):
    service = battle_context["service"]

    with pytest.raises(SameBattleParticipant):
        await service.create_challenge(
            initiator_trainer_id=INITIATOR_ID,
            opponent_trainer_id=INITIATOR_ID,
            created_at=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_set_party_marks_battle_ready_when_both_teams_locked(battle_context):
    service = battle_context["service"]

    battle = await service.create_challenge(
        initiator_trainer_id=INITIATOR_ID,
        opponent_trainer_id=OPPONENT_ID,
        created_at=datetime.now(UTC),
    )

    await service.set_party_from_collection_numbers(
        battle.id,
        INITIATOR_ID,
        [1, 2, 3],
    )
    battle = await service.set_party_from_collection_numbers(
        battle.id,
        OPPONENT_ID,
        [4, 5, 6],
    )

    assert battle.is_ready


@pytest.mark.asyncio
async def test_set_party_rejects_creature_not_on_team(battle_context):
    service = battle_context["service"]

    battle = await service.create_challenge(
        initiator_trainer_id=INITIATOR_ID,
        opponent_trainer_id=OPPONENT_ID,
        created_at=datetime.now(UTC),
    )

    with pytest.raises(BattleCreatureNotOnTeam):
        await service.set_party_from_collection_numbers(
            battle.id,
            INITIATOR_ID,
            [1, 2, 99],
        )
