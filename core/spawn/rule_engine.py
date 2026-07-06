from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.rule import Rule
from core.species.species import Species


class RuleEngine:
    """
    Applies spawn rules to a collection of species.
    """

    def apply(
        self,
        species_pool: tuple[Species, ...],
        rules: tuple[Rule, ...],
        context: SpawnContext,
        profile: SpawnProfile,
    ) -> tuple[Species, ...]:
        """
        Returns only the species allowed by every rule.
        """

        return tuple(
            candidate
            for candidate in species_pool
            if all(rule.allows(candidate, context, profile) for rule in rules)
        )
