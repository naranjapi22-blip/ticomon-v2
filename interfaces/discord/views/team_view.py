from __future__ import annotations

import discord

from application.bootstrap.core import CoreServices
from application.team.exceptions import TeamApplicationError
from application.team.team_dto import TeamDTO
from interfaces.discord.cogs.collection_display import format_creature_entry
from interfaces.discord.views.team_add_modal import TeamAddModal
from interfaces.discord.views.team_replace_modal import TeamReplaceModal


class TeamView(discord.ui.View):
    def __init__(
        self,
        core: CoreServices,
        trainer_id: int,
        team: TeamDTO,
    ) -> None:
        super().__init__(timeout=300)

        self.core = core
        self.trainer_id = trainer_id
        self.team = team
        self.message: discord.Message | None = None

        self._sync_buttons()

    @classmethod
    async def create(
        cls,
        core: CoreServices,
        trainer_id: int,
    ) -> TeamView:
        team = await core.team_application_service.get_team(trainer_id)
        return cls(
            core,
            trainer_id,
            team,
        )

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Your Team",
            description=self._build_description(),
            color=discord.Color.green(),
        )
        embed.set_footer(
            text=f"{len(self.team.slots)}/9 Pokémon assigned",
        )
        return embed

    def _build_description(self) -> str:
        if not self.team.slots:
            return (
                "Your team is empty.\n"
                "Use **Add** to assign Pokémon from your collection."
            )

        lines = [
            f"**Slot {slot.slot}:** {format_creature_entry(slot.creature)}"
            for slot in self.team.slots
        ]
        return "\n".join(lines)

    def _sync_buttons(self) -> None:
        for child in self.children:
            if not isinstance(child, discord.ui.Button):
                continue

            if child.custom_id == "team:add":
                child.disabled = len(self.team.slots) >= 9
            elif child.custom_id == "team:remove_last":
                child.disabled = not self.team.slots
            elif child.custom_id == "team:replace":
                child.disabled = not self.team.slots

    async def refresh(self) -> None:
        self.team = await self.core.team_application_service.get_team(
            self.trainer_id,
        )
        self._sync_buttons()

        if self.message is not None:
            await self.message.edit(
                embed=self.build_embed(),
                view=self,
            )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id != self.trainer_id:
            await interaction.response.send_message(
                "❌ This is not your team.",
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

    @discord.ui.button(
        label="Add",
        style=discord.ButtonStyle.success,
        emoji="➕",
        custom_id="team:add",
    )
    async def add_to_team(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.send_modal(
            TeamAddModal(
                self.core,
                trainer_id=self.trainer_id,
                team_view=self,
            )
        )

    @discord.ui.button(
        label="Remove Last",
        style=discord.ButtonStyle.danger,
        emoji="➖",
        custom_id="team:remove_last",
    )
    async def remove_last(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not self.team.slots:
            await interaction.response.send_message(
                "❌ Your team is empty.",
                ephemeral=True,
            )
            return

        last_slot = max(self.team.slots, key=lambda slot: slot.slot)

        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )

        try:
            await self.core.team_application_service.remove_from_team(
                trainer_id=self.trainer_id,
                collection_number=last_slot.creature.collection_number,
            )
        except TeamApplicationError as error:
            await interaction.followup.send(
                f"❌ {error}",
                ephemeral=True,
            )
            return

        await self.refresh()
        await interaction.followup.send(
            (
                f"✅ Removed #{last_slot.creature.collection_number} "
                f"{last_slot.creature.species.name.title()} from slot "
                f"{last_slot.slot}."
            ),
            ephemeral=True,
        )

    @discord.ui.button(
        label="Replace",
        style=discord.ButtonStyle.primary,
        emoji="🔄",
        custom_id="team:replace",
    )
    async def replace_team_member(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.send_modal(
            TeamReplaceModal(
                self.core,
                trainer_id=self.trainer_id,
                team_view=self,
            )
        )
