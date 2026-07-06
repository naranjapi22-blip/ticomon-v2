from core.evolution.evolution_stage import EvolutionStage


class StageResolver:

    def resolve(
        self,
        chain: dict,
        species_name: str,
    ) -> EvolutionStage:

        depth = self._find_depth(
            node=chain["chain"],
            species_name=species_name,
            depth=0,
        )

        if depth == 0:
            return EvolutionStage.FIRST

        if depth == 1:
            return EvolutionStage.SECOND

        return EvolutionStage.FINAL

    def _find_depth(
        self,
        *,
        node: dict,
        species_name: str,
        depth: int,
    ) -> int:
        if node["species"]["name"] == species_name:
            return depth

        for child in node["evolves_to"]:
            result = self._find_depth(
                node=child,
                species_name=species_name,
                depth=depth + 1,
            )

            if result != -1:
                return result

        return -1
