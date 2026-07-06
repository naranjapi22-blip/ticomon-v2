from core.evolution.evolution_stage import EvolutionStage
from core.evolution.stage_resolver import StageResolver


def test_bulbasaur_is_first_stage():
    resolver = StageResolver()

    chain = {
        "chain": {
            "species": {"name": "bulbasaur"},
            "evolves_to": [
                {
                    "species": {"name": "ivysaur"},
                    "evolves_to": [
                        {
                            "species": {"name": "venusaur"},
                            "evolves_to": [],
                        }
                    ],
                }
            ],
        }
    }

    stage = resolver.resolve(
        chain=chain,
        species_name="bulbasaur",
    )

    assert stage == EvolutionStage.FIRST


def test_ivysaur_is_second_stage():
    resolver = StageResolver()

    chain = {
        "chain": {
            "species": {"name": "bulbasaur"},
            "evolves_to": [
                {
                    "species": {"name": "ivysaur"},
                    "evolves_to": [
                        {
                            "species": {"name": "venusaur"},
                            "evolves_to": [],
                        }
                    ],
                }
            ],
        }
    }

    stage = resolver.resolve(
        chain=chain,
        species_name="ivysaur",
    )

    assert stage == EvolutionStage.SECOND


def test_venusaur_is_final_stage():
    resolver = StageResolver()

    chain = {
        "chain": {
            "species": {"name": "bulbasaur"},
            "evolves_to": [
                {
                    "species": {"name": "ivysaur"},
                    "evolves_to": [
                        {
                            "species": {"name": "venusaur"},
                            "evolves_to": [],
                        }
                    ],
                }
            ],
        }
    }

    stage = resolver.resolve(
        chain=chain,
        species_name="venusaur",
    )

    assert stage == EvolutionStage.FINAL
