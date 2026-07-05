from core.capture.capture_service import CaptureService
from core.opportunity.opportunity_factory import OpportunityFactory
from core.species.species import Species
from core.creature.base_stats import BaseStats


def test_capture_service_flow():
    service = CaptureService()

    # 🧬 Species REAL (gameplay model)
    species = Species(
        id=1,
        name="pikachu",
        types=["electric"],
        base_stats=BaseStats(
            hp=35,
            attack=55,
            defense=40,
            special_attack=50,
            special_defense=50,
            speed=90,
        ),
        height=4,
        weight=60,
        capture_rate=190,
        evolution_chain=None,
        variants=[],
    )

    # 🎯 ahora Opportunity usa Species real
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
