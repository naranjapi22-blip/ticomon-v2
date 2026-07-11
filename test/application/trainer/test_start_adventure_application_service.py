import pytest

from application.adventure.start_adventure.exceptions import (
    TrainerAlreadyExistsError,
)
from application.adventure.start_adventure.start_adventure_application_service import (
    StartAdventureApplicationService,
)
from core.trainer.trainer_factory import TrainerFactory
from test.builders.species_builder import SpeciesBuilder
from test.fakes.fake_creature_repository import FakeCreatureRepository
from test.fakes.fake_species_repository import FakeSpeciesRepository
from test.fakes.fake_trainer_repository import FakeTrainerRepository


@pytest.mark.asyncio
async def test_start_adventure_creates_trainer_and_starter():

    species = SpeciesBuilder().with_id(1).build()

    species_repository = FakeSpeciesRepository(
        species,
    )

    creature_repository = FakeCreatureRepository()

    trainer_repository = FakeTrainerRepository()

    service = StartAdventureApplicationService(
        species_repository=species_repository,
        creature_repository=creature_repository,
        trainer_repository=trainer_repository,
    )

    result = await service.start(
        trainer_id=1,
        starter_species_id=1,
    )

    assert result.trainer.trainer_id == 1
    assert result.starter.species.id == 1

    assert await trainer_repository.exists(
        1,
    )

    assert result.starter in creature_repository.saved


@pytest.mark.asyncio
async def test_start_adventure_raises_when_trainer_already_exists():

    species = SpeciesBuilder().with_id(1).build()

    species_repository = FakeSpeciesRepository(
        species,
    )

    creature_repository = FakeCreatureRepository()

    trainer_repository = FakeTrainerRepository()

    trainer = TrainerFactory.create(
        trainer_id=1,
        starter_creature_id=100,
    )

    await trainer_repository.save(
        trainer,
    )

    service = StartAdventureApplicationService(
        species_repository=species_repository,
        creature_repository=creature_repository,
        trainer_repository=trainer_repository,
    )

    with pytest.raises(
        TrainerAlreadyExistsError,
    ):
        await service.start(
            trainer_id=1,
            starter_species_id=1,
        )
