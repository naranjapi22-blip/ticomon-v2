import discord

from interfaces.discord.buttons.opportunity_button import OpportunityButton


class SpawnView(discord.ui.View):
    def __init__(self, core, session):
        super().__init__(timeout=300)
        self._core = core
        self._session = session

        for index, opportunity in enumerate(
            session.opportunities,
            start=1,
        ):
            self.add_item(
                OpportunityButton(
                    core=self._core,
                    index=index,
                    label=opportunity.species.name,
                )
            )
