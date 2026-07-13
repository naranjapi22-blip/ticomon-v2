from __future__ import annotations

import math

import discord

from interfaces.discord.views.next_button import NextButton
from interfaces.discord.views.previous_button import PreviousButton


class CreatureListView(discord.ui.View):
    PAGE_SIZE = 10

    def __init__(
        self,
        author_id: int,
        title: str,
        entries: list[str],
    ) -> None:
        super().__init__(timeout=300)

        self.author_id = author_id
        self.title = title
        self.entries = entries
        self.page = 0
        self.total_pages = max(
            1,
            math.ceil(len(entries) / self.PAGE_SIZE),
        )
        self.message: discord.Message | None = None

        self.previous_button = PreviousButton()
        self.next_button = NextButton()

        self.add_item(self.previous_button)
        self.add_item(self.next_button)

        self._sync_buttons()

    def _sync_buttons(self) -> None:
        self.previous_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= self.total_pages - 1

    def _page_entries(self) -> list[str]:
        start = self.page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        return self.entries[start:end]

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.title,
            description="\n".join(self._page_entries()),
            color=discord.Color.blurple(),
        )

        embed.set_footer(
            text=f"Page {self.page + 1}/{self.total_pages}",
        )

        return embed

    async def refresh(self, interaction: discord.Interaction) -> None:
        self._sync_buttons()

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self,
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ This isn't your list.",
                ephemeral=True,
            )
            return False

        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True

        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
