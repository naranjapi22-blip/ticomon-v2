from core.battle.ports.damage_calculator import (
    LearnsetProvider,
    SpeciesLearnset,
    SpeciesLearnsetQuery,
)
from core.battle.rules.move_policy import MoveData


class FakeLearnsetProvider(LearnsetProvider):
    def get_learnset(self, query: SpeciesLearnsetQuery) -> SpeciesLearnset:
        return SpeciesLearnset(
            species_showdown_id=query.species_name.lower(),
            moves={
                "tackle": MoveData(
                    move_id="tackle",
                    display_name="Tackle",
                    category="Physical",
                    move_type="normal",
                    base_power=40,
                    accuracy=100,
                ),
                "ember": MoveData(
                    move_id="ember",
                    display_name="Ember",
                    category="Special",
                    move_type="fire",
                    base_power=40,
                    accuracy=100,
                ),
            },
        )
