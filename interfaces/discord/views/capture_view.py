import discord

from interfaces.discord.buttons.capture_button import CaptureButton


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
