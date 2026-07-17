import pytest

from application.team.exceptions import (
    TeamCreatureAlreadyInTeam,
    TeamCreatureNotInTeam,
    TeamFull,
    TeamInsufficientCreatures,
)
from application.team.team_application_service import TeamApplicationService
from test.builders.creature_builder import CreatureBuilder
from test.fakes.fake_creature_repository import FakeCreatureRepository
from test.fakes.fake_team_repository import FakeTeamRepository

TRAINER_ID = 42


def build_creature(
    *,
    creature_id: int,
    collection_number: int,
):
    return (
        CreatureBuilder()
        .with_id(creature_id)
        .with_trainer_id(TRAINER_ID)
        .with_collection_number(collection_number)
        .build()
    )


@pytest.fixture
def service_context():
    creatures = [
        build_creature(creature_id=101, collection_number=1),
        build_creature(creature_id=102, collection_number=2),
        build_creature(creature_id=103, collection_number=3),
        build_creature(creature_id=104, collection_number=4),
    ]
    creature_repository = FakeCreatureRepository(*creatures)
    team_repository = FakeTeamRepository()

    return {
        "service": TeamApplicationService(
            creature_repository=creature_repository,
            team_repository=team_repository,
        ),
        "creature_repository": creature_repository,
        "team_repository": team_repository,
        "creatures": creatures,
    }


@pytest.mark.asyncio
async def test_get_team_returns_all_slots_with_creatures(service_context):
    service = service_context["service"]

    await service.add_to_team(
        trainer_id=TRAINER_ID,
        collection_number=1,
    )
    await service.add_to_team(
        trainer_id=TRAINER_ID,
        collection_number=3,
    )

    team = await service.get_team(TRAINER_ID)

    assert len(team.slots) == 2
    assert team.slots[0].slot == 1
    assert team.slots[0].creature.collection_number == 1
    assert team.slots[1].slot == 2
    assert team.slots[1].creature.collection_number == 3


@pytest.mark.asyncio
async def test_add_to_team_assigns_first_available_slot(service_context):
    await service_context["service"].add_to_team(
        trainer_id=TRAINER_ID,
        collection_number=1,
    )

    team = await service_context["service"].get_team(TRAINER_ID)

    assert len(team.slots) == 1
    assert team.slots[0].slot == 1
    assert team.slots[0].creature.id == 101


@pytest.mark.asyncio
async def test_add_to_team_fills_lowest_available_slot(service_context):
    service = service_context["service"]

    await service.add_to_team(
        trainer_id=TRAINER_ID,
        collection_number=1,
    )
    await service.add_to_team(
        trainer_id=TRAINER_ID,
        collection_number=2,
    )
    await service.remove_from_team(
        trainer_id=TRAINER_ID,
        collection_number=2,
    )
    await service.add_to_team(
        trainer_id=TRAINER_ID,
        collection_number=3,
    )

    team = await service.get_team(TRAINER_ID)

    assert [(slot.slot, slot.creature.collection_number) for slot in team.slots] == [
        (1, 1),
        (2, 3),
    ]


@pytest.mark.asyncio
async def test_add_to_team_rejects_trainers_with_fewer_than_three_creatures(
    service_context,
):
    service_context["creature_repository"]._creatures.pop(104)
    service_context["creature_repository"]._creatures.pop(103)
    service_context["creature_repository"]._collection_numbers.pop(4)
    service_context["creature_repository"]._collection_numbers.pop(3)

    with pytest.raises(TeamInsufficientCreatures):
        await service_context["service"].add_to_team(
            trainer_id=TRAINER_ID,
            collection_number=1,
        )


@pytest.mark.asyncio
async def test_add_to_team_rejects_creature_already_in_team(service_context):
    service = service_context["service"]

    await service.add_to_team(
        trainer_id=TRAINER_ID,
        collection_number=1,
    )

    with pytest.raises(TeamCreatureAlreadyInTeam):
        await service.add_to_team(
            trainer_id=TRAINER_ID,
            collection_number=1,
        )


@pytest.mark.asyncio
async def test_add_to_team_rejects_when_team_is_full(service_context):
    service = service_context["service"]

    for slot in range(1, 10):
        creature = (
            CreatureBuilder()
            .with_id(200 + slot)
            .with_trainer_id(TRAINER_ID)
            .with_collection_number(10 + slot)
            .build()
        )
        await service_context["creature_repository"].save(creature)
        await service.add_to_team(
            trainer_id=TRAINER_ID,
            collection_number=10 + slot,
        )

    extra_creature = (
        CreatureBuilder()
        .with_id(999)
        .with_trainer_id(TRAINER_ID)
        .with_collection_number(99)
        .build()
    )
    await service_context["creature_repository"].save(extra_creature)

    with pytest.raises(TeamFull):
        await service.add_to_team(
            trainer_id=TRAINER_ID,
            collection_number=99,
        )


@pytest.mark.asyncio
async def test_replace_in_team_swaps_creature_in_same_slot(service_context):
    service = service_context["service"]

    await service.add_to_team(
        trainer_id=TRAINER_ID,
        collection_number=1,
    )
    await service.replace_in_team(
        trainer_id=TRAINER_ID,
        collection_number_to_replace=1,
        new_collection_number=4,
    )

    team = await service.get_team(TRAINER_ID)

    assert len(team.slots) == 1
    assert team.slots[0].slot == 1
    assert team.slots[0].creature.id == 104


@pytest.mark.asyncio
async def test_replace_in_team_rejects_creature_not_in_team(service_context):
    with pytest.raises(TeamCreatureNotInTeam):
        await service_context["service"].replace_in_team(
            trainer_id=TRAINER_ID,
            collection_number_to_replace=2,
            new_collection_number=3,
        )


@pytest.mark.asyncio
async def test_remove_from_team_deletes_assignment(service_context):
    service = service_context["service"]

    await service.add_to_team(
        trainer_id=TRAINER_ID,
        collection_number=2,
    )
    await service.remove_from_team(
        trainer_id=TRAINER_ID,
        collection_number=2,
    )

    team = await service.get_team(TRAINER_ID)
    assert team.slots == ()


@pytest.mark.asyncio
async def test_remove_from_team_rejects_creature_not_in_team(service_context):
    with pytest.raises(TeamCreatureNotInTeam):
        await service_context["service"].remove_from_team(
            trainer_id=TRAINER_ID,
            collection_number=3,
        )
