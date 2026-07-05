from core.spawn.spawn_service import SpawnService


def test_spawn_from_db():
    service = SpawnService()

    opportunity = service.spawn()

    assert opportunity is not None
    assert opportunity.species is not None
    assert opportunity.species.name is not None
    assert isinstance(opportunity.species.types, list)
