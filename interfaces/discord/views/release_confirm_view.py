import discord

from interfaces.discord.buttons.release_cancel_button import (
    ReleaseCancelButton,
)
from interfaces.discord.buttons.release_confirm_button import (
    ReleaseConfirmButton,
)


class ReleaseConfirmView(discord.ui.View):

    def __init__(
        self,
        core,
        trainer_id: int,
        collection_numbers: list[int],
    ):
        super().__init__(
            timeout=60,
        )

        self.add_item(
            ReleaseConfirmButton(
                core=core,
                trainer_id=trainer_id,
                collection_numbers=collection_numbers,
            )
        )

        self.add_item(ReleaseCancelButton())
