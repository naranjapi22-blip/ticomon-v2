import discord

from interfaces.discord.buttons.capture_button import CaptureButton
from interfaces.discord.buttons.pokedex_button import PokedexButton


class CaptureView(discord.ui.View):
    def __init__(self, core):
        super().__init__(timeout=300)

        self._core = core
        self.message: discord.Message | None = None

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

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
