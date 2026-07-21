from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

import discord

logger = logging.getLogger(__name__)


class CreatureSelectionView(discord.ui.View):
    """Private, owner-bound collection picker shared by battle-like flows."""

    def __init__(
        self,
        *,
        owner_id: int,
        required_count: int,
        options: list[tuple[int, str]],
        on_selected: Callable[[list[int]], Awaitable[object]],
        success_message: Callable[[object], str],
        success_view: Callable[[object], discord.ui.View | None] | None = None,
        error_prefix: str = "❌ Could not save team: ",
        timeout: float = 180,
    ) -> None:
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.required_count = required_count
        self._on_selected = on_selected
        self._success_message = success_message
        self._success_view = success_view
        self._error_prefix = error_prefix

        select = discord.ui.Select(
            placeholder=f"Choose {required_count} team members",
            min_values=required_count,
            max_values=required_count,
            options=[
                discord.SelectOption(label=label[:100], value=str(number))
                for number, label in options[:25]
            ],
        )
        select.callback = self.on_select
        self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            try:
                await interaction.response.send_message(
                    "❌ This team selection is not yours.", ephemeral=True
                )
            except (discord.NotFound, discord.HTTPException):
                logger.debug("Unable to reject non-owner team selection", exc_info=True)
            return False
        return True

    async def on_select(self, interaction: discord.Interaction) -> None:
        selected = [int(value) for value in interaction.data.get("values", [])]
        try:
            await interaction.response.defer(ephemeral=True)
        except (discord.NotFound, discord.HTTPException):
            logger.debug("Unable to defer team selection interaction", exc_info=True)
            return
        if len(selected) != self.required_count or len(set(selected)) != len(selected):
            await self._followup(
                interaction,
                (
                    f"{self._error_prefix}select exactly {self.required_count} "
                    "different creatures."
                ),
            )
            return
        try:
            result = await self._on_selected(selected)
        except Exception as error:
            await self._followup(interaction, f"{self._error_prefix}{error}")
            return
        await self._followup(
            interaction,
            self._success_message(result),
            view=self._success_view(result) if self._success_view else None,
        )
        self.stop()

    async def _followup(self, interaction, content: str, **kwargs) -> None:
        try:
            await interaction.followup.send(content, ephemeral=True, **kwargs)
        except (discord.NotFound, discord.HTTPException):
            logger.debug("Unable to send team selection followup", exc_info=True)

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
