import math

import discord

from interfaces.discord.views.next_button import NextButton
from interfaces.discord.views.previous_button import PreviousButton

FAMILIES = ("Capture", "Pokédex", "Shiny", "Safari", "Trade", "Special", "Types")


class _FamilyButton(discord.ui.Button):
    def __init__(self, family: str) -> None:
        super().__init__(label=family, style=discord.ButtonStyle.primary)
        self.family = family

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        view.family = self.family
        view.page = 0
        await view.refresh(interaction)


class _OverviewButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Overview", style=discord.ButtonStyle.secondary, row=2)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        view.family = None
        view.page = 0
        await view.refresh(interaction)


class AchievementsView(discord.ui.View):
    PAGE_SIZE = 6

    def __init__(self, trainer_id: int, statuses) -> None:
        super().__init__(timeout=300)
        self.trainer_id = trainer_id
        self.statuses = tuple(statuses)
        self.family: str | None = None
        self.page = 0
        self.message: discord.Message | None = None
        self.previous_button = PreviousButton()
        self.next_button = NextButton()
        self.previous_button.label = "Previous"
        self.next_button.label = "Next"
        self._build_components()

    def _build_components(self) -> None:
        self.clear_items()
        for family in FAMILIES:
            self.add_item(_FamilyButton(family))
        self.add_item(self.previous_button)
        self.add_item(self.next_button)
        self.add_item(_OverviewButton())
        self._sync_buttons()

    def _family_statuses(self):
        return tuple(status for status in self.statuses if status.family == self.family)

    @property
    def total_pages(self) -> int:
        if self.family is None:
            return 1
        return max(1, math.ceil(len(self._family_statuses()) / self.PAGE_SIZE))

    def _sync_buttons(self) -> None:
        self.previous_button.disabled = self.family is None or self.page <= 0
        self.next_button.disabled = (
            self.family is None or self.page >= self.total_pages - 1
        )

    @staticmethod
    def _reward(status) -> str:
        if status.rewarded_candies is not None:
            return ", ".join(
                f"{kind.value.title()} +{amount}"
                for kind, amount in status.rewarded_candies.items()
            )
        return f"{status.configured_reward} candies"

    def _entry(self, status) -> str:
        state = "Unlocked" if status.unlocked else "In progress"
        detail = (
            f"Unlocked: {status.unlocked_at:%Y-%m-%d}"
            if status.unlocked
            else f"Progress: {status.progress}/{status.threshold}"
        )
        return (
            f"**{state} — {status.name}**\n{status.description}\n"
            f"{detail} • Reward: {self._reward(status)}"
        )

    def build_embed(self) -> discord.Embed:
        unlocked = sum(status.unlocked for status in self.statuses)
        if self.family is None:
            percentage = unlocked / len(self.statuses) * 100 if self.statuses else 0
            return discord.Embed(
                title="Achievements",
                description=(
                    f"Unlocked: **{unlocked}/{len(self.statuses)}**\n"
                    f"Completion: **{percentage:.1f}%**\n\n"
                    "Choose a family to view its achievements."
                ),
                color=discord.Color.gold(),
            )

        entries = self._family_statuses()
        family_unlocked = sum(status.unlocked for status in entries)
        start = self.page * self.PAGE_SIZE
        page_entries = entries[start : start + self.PAGE_SIZE]
        embed = discord.Embed(
            title=f"Achievements — {self.family}",
            description=f"Unlocked: **{family_unlocked}/{len(entries)}**",
            color=discord.Color.gold(),
        )
        embed.add_field(
            name="Achievements",
            value="\n\n".join(self._entry(status) for status in page_entries) or "None",
            inline=False,
        )
        embed.set_footer(text=f"Page {self.page + 1}/{self.total_pages}")
        return embed

    async def refresh(self, interaction: discord.Interaction) -> None:
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.trainer_id:
            await interaction.response.send_message(
                "❌ This achievement view belongs to another trainer.", ephemeral=True
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
