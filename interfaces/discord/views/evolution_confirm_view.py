import discord

from core.evolution.evolution_rule import EvolutionRule
from interfaces.discord.buttons.evolution_cancel_button import (
    EvolutionCancelButton,
)
from interfaces.discord.buttons.evolution_confirm_button import (
    EvolutionConfirmButton,
)


class EvolutionConfirmView(discord.ui.View):

    def __init__(
        self,
        core,
        trainer_id: int,
        collection_number: int,
        rule: EvolutionRule,
    ):
        super().__init__(
            timeout=60,
        )
        self._processing = False

        self.add_item(
            EvolutionConfirmButton(
                core=core,
                trainer_id=trainer_id,
                collection_number=collection_number,
                rule=rule,
            )
        )

        self.add_item(EvolutionCancelButton())

    def begin_processing(self) -> bool:
        if self._processing:
            return False
        self._processing = True
        for child in self.children:
            child.disabled = True
        return True
