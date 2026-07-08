import discord

from interfaces.discord.buttons.capture_button import CaptureButton
from interfaces.discord.buttons.pokedex_button import PokedexButton


class CaptureView(discord.ui.View):
    def __init__(self, core):
        super().__init__(timeout=60)

        self._core = core
        self._session = None

        self.add_item(
            CaptureButton(
                self._core,
            )
        )

        self.add_item(
            PokedexButton(
                self._core,
            )
        )
