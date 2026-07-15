import pytest

from application.profile.profile_service import ProfileService


class _CreatureRepository:
    async def count_creatures(self, trainer_id: int) -> int:
        return 0

    async def count_species(self, trainer_id: int) -> int:
        return 0

    async def count_shinies(self, trainer_id: int) -> int:
        return 0


class _ProfileRepository:
    def __init__(self) -> None:
        self.write_calls = 0

    async def get_featured_creature_id(self, trainer_id: int):
        return None

    async def get_selected_trainer(self, trainer_id: int) -> int:
        return 1

    async def set_featured_creature(self, trainer_id: int, creature_id: int) -> None:
        self.write_calls += 1

    async def set_selected_trainer(
        self,
        trainer_id: int,
        selected_trainer: int,
    ) -> None:
        self.write_calls += 1


@pytest.mark.asyncio
async def test_get_profile_has_no_persistence_side_effects() -> None:
    profile_repository = _ProfileRepository()
    service = ProfileService(_CreatureRepository(), profile_repository)

    await service.get_profile(1)

    assert profile_repository.write_calls == 0
