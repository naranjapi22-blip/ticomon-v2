from application.bootstrap import core as bootstrap_core
from infrastructure.persistence.repositories.neon_release_unit_of_work import (
    NeonReleaseUnitOfWork,
)


def test_build_core_injects_neon_release_unit_of_work(monkeypatch):
    captured = {}

    class SpyReleaseApplicationService:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        bootstrap_core,
        "ReleaseApplicationService",
        SpyReleaseApplicationService,
    )

    bootstrap_core.build_core()

    assert isinstance(captured["unit_of_work"], NeonReleaseUnitOfWork)
