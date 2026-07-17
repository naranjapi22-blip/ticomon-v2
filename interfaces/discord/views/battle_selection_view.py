from __future__ import annotations

import discord

from application.battle.exceptions import BattleApplicationError, BattleNotFound
from application.bootstrap.core import CoreServices
from core.battle.battle import PARTY_SIZE
from core.battle.exceptions import (
    BattleNotParticipant,
    InvalidBattleParty,
    InvalidBattleState,
)


class BattleSelectionView(discord.ui.View):
    def __init__(
        self,
        core: CoreServices,
        battle_id: int,
        trainer_id: int,
        options: list[tuple[int, str]],
        challenge_view: "BattleChallengeView",
    ) -> None:
        super().__init__(timeout=180)
        self.core = core
        self.battle_id = battle_id
        self.trainer_id = trainer_id
        self.challenge_view = challenge_view

        select = discord.ui.Select(
            placeholder=f"Choose {PARTY_SIZE} team members",
            min_values=PARTY_SIZE,
            max_values=PARTY_SIZE,
            options=[
                discord.SelectOption(
                    label=label[:100],
                    value=str(collection_number),
                )
                for collection_number, label in options[:25]
            ],
        )
        select.callback = self.on_select
        self.add_item(select)

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id != self.trainer_id:
            await interaction.response.send_message(
                "❌ This team selection is not yours.",
                ephemeral=True,
            )
            return False
        return True

    async def on_select(self, interaction: discord.Interaction) -> None:
        selected = [int(value) for value in interaction.data.get("values", [])]

        await interaction.response.defer(ephemeral=True)

        try:
            battle = await self.core.battle_application_service.set_party_from_collection_numbers(
                self.battle_id,
                self.trainer_id,
                selected,
            )
        except (
            BattleNotFound,
            BattleNotParticipant,
            InvalidBattleParty,
            InvalidBattleState,
            BattleApplicationError,
        ) as error:
            await interaction.followup.send(
                f"❌ Could not save team: {error}",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"✅ Your battle team is locked ({PARTY_SIZE} Pokémon).",
            ephemeral=True,
        )

        await self.challenge_view.refresh_display(battle)
        self.stop()


class BattleChallengeView(discord.ui.View):
    def __init__(
        self,
        core: CoreServices,
        battle_id: int,
        initiator_id: int,
        opponent_id: int,
    ) -> None:
        super().__init__(timeout=180)
        self.core = core
        self.battle_id = battle_id
        self.initiator_id = initiator_id
        self.opponent_id = opponent_id
        self.message: discord.Message | None = None

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id not in {self.initiator_id, self.opponent_id}:
            await interaction.response.send_message(
                "❌ You are not part of this battle.",
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
        label="Pick Your Team",
        style=discord.ButtonStyle.primary,
        emoji="📋",
    )
    async def pick_team(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            options = await self.core.battle_application_service.get_team_selector(
                interaction.user.id,
            )
            battle = await self.core.battle_application_service.get_battle(
                self.battle_id,
            )
        except BattleNotFound as error:
            await interaction.followup.send(f"❌ {error}", ephemeral=True)
            return

        if battle.has_party(interaction.user.id):
            await interaction.followup.send(
                "✅ You already locked your team.",
                ephemeral=True,
            )
            return

        if len(options) < PARTY_SIZE:
            await interaction.followup.send(
                f"❌ You need at least {PARTY_SIZE} Pokémon on your saved team.",
                ephemeral=True,
            )
            return

        selection_view = BattleSelectionView(
            self.core,
            self.battle_id,
            interaction.user.id,
            options,
            challenge_view=self,
        )

        await interaction.followup.send(
            embed=discord.Embed(
                title="Select Battle Team",
                description=(
                    f"Choose exactly **{PARTY_SIZE}** Pokémon from your saved team."
                ),
                color=discord.Color.blue(),
            ),
            view=selection_view,
            ephemeral=True,
        )

    async def refresh_display(self, battle) -> None:
        if self.message is None:
            return

        if battle.is_ready:
            from interfaces.discord.views.battle_arena_view import BattleArenaView

            arena_view = BattleArenaView(
                self.core,
                self.battle_id,
                self.initiator_id,
                self.opponent_id,
            )
            arena_view.message = self.message
            await self.message.edit(
                embed=arena_view.build_embed(battle),
                view=arena_view,
            )
            self.stop()
            return

        await self.message.edit(
            embed=self.build_embed(battle),
            view=self,
        )

    def build_embed(self, battle) -> discord.Embed:
        initiator_status = (
            "✅ Ready" if battle.has_party(self.initiator_id) else "⏳ Picking"
        )
        opponent_status = (
            "✅ Ready" if battle.has_party(self.opponent_id) else "⏳ Picking"
        )

        return (
            discord.Embed(
                title="⚔️ Battle Challenge",
                description=(
                    f"<@{self.initiator_id}> challenged <@{self.opponent_id}>!\n"
                    f"Each trainer must privately pick **{PARTY_SIZE}** Pokémon."
                ),
                color=discord.Color.red(),
            )
            .add_field(
                name="Initiator",
                value=f"<@{self.initiator_id}> — {initiator_status}",
                inline=False,
            )
            .add_field(
                name="Opponent",
                value=f"<@{self.opponent_id}> — {opponent_status}",
                inline=False,
            )
        )
