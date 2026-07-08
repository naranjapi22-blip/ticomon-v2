from dataclasses import dataclass, field
from datetime import datetime

from core.opportunity.opportunity import Opportunity


@dataclass(slots=True)
class SpawnSession:
    """
    Represents an active spawn containing capture opportunities.
    """

    owner_id: int

    opportunities: list[Opportunity]

    selected_opportunity: Opportunity | None = None

    created_at: datetime = field(default_factory=datetime.utcnow)

    def get_opportunity(
        self,
        index: int,
    ) -> Opportunity:
        """
        Returns the selected opportunity using a 1-based index.
        """

        return self.opportunities[index - 1]

    def select_opportunity(
        self,
        index: int,
    ) -> Opportunity:
        """
        Selects an opportunity for the active capture session.
        """

        if self.selected_opportunity is not None:
            return self.selected_opportunity

        opportunity = self.get_opportunity(index)

        self.selected_opportunity = opportunity

        return opportunity
