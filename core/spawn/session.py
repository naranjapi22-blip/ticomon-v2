from dataclasses import dataclass

from core.opportunity.opportunity import Opportunity


@dataclass(slots=True)
class SpawnSession:
    """
    Represents an active spawn containing capture opportunities.
    """

    opportunities: list[Opportunity]

    def get_opportunity(
        self,
        index: int,
    ) -> Opportunity:
        """
        Returns the selected opportunity using a 1-based index.
        """

        return self.opportunities[index - 1]

    def remove_opportunity(
        self,
        index: int,
    ) -> None:
        """
        Removes a captured opportunity from the active session.
        """

        self.opportunities.pop(index - 1)
