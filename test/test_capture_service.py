from core.capture.capture_service import CaptureService
from core.opportunity.opportunity_factory import OpportunityFactory


class FakeSpecies:
    def __init__(self):
        self.name = "pikachu"
        self.default_form = "base"
        self.variants = []   # 👈 FIX CLAVE


def test_capture_service_flow():
    service = CaptureService()

    species = FakeSpecies()
    opportunity = OpportunityFactory.create(species)

    result = service.capture(
        opportunity=opportunity,
        trainer_id="trainer_1",
        creature_id=1
    )

    assert result.success in [True, False]

    if result.success:
        assert result.creature is not None
        assert result.creature.trainer_id == "trainer_1"
    else:
        assert result.creature is None