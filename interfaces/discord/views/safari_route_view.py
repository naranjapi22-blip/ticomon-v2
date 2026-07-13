from __future__ import annotations

import discord

from application.bootstrap.core import CoreServices
from application.safari import (
    SafariRouteVoteNotFound,
    SafariRouteVoteUnavailable,
    SafariSessionNotFound,
)
from core.safari import SafariRouteOption, SafariRouteVote, SafariSession
from interfaces.discord.views.safari_encounter_view import SafariEncounterView
from rendering.safari.narrative import route_narrative


class SafariRouteOptionSelect(discord.ui.Select):
    def __init__(self, view: "SafariRouteView") -> None:
        options = []
        for option in view.options:
            destination = option.destination_zone.value.replace("_", " ").title()
            movement = "Stay" if option.stays_in_same_zone else "Advance"
            options.append(
                discord.SelectOption(
                    label=f"{movement}: {destination}",
                    value=option.id,
                    description=option.narrative_key.replace("_", " "),
                )
            )

        super().__init__(
            placeholder="Vote for the next route...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.cast_vote(interaction, self.values[0])


class SafariRouteResolveButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label="Resolve Route",
            style=discord.ButtonStyle.primary,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.resolve_route(interaction)


class SafariRouteView(discord.ui.View):
    def __init__(
        self,
        core: CoreServices,
        guild_id: int,
        session: SafariSession,
        vote: SafariRouteVote,
        options: tuple[SafariRouteOption, ...],
    ) -> None:
        super().__init__(timeout=300)

        self.core = core
        self.guild_id = guild_id
        self.session = session
        self.vote = vote
        self.options = options
        self.message: discord.Message | None = None

        self.add_item(SafariRouteOptionSelect(self))
        self.add_item(SafariRouteResolveButton())

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Safari Route Vote",
            description=route_narrative(
                self.session.safari_map,
                len(self.options),
            ),
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Map", value=self.session.safari_map.value, inline=True)
        embed.add_field(
            name="Zone", value=self.session.current_segment.zone.value, inline=True
        )
        embed.add_field(name="Weather", value=self.session.weather.value, inline=True)
        embed.add_field(name="Time", value=self.session.time_of_day.value, inline=True)
        embed.add_field(
            name="Votes", value=str(len(self.vote.votes_by_trainer)), inline=True
        )
        embed.add_field(
            name="Choices",
            value="\n".join(
                (
                    f"**{option.id}** — "
                    f"{'Stay' if option.stays_in_same_zone else 'Advance'} "
                    f"to {option.destination_zone.value.replace('_', ' ').title()}"
                )
                for option in self.options
            ),
            inline=False,
        )
        return embed

    async def cast_vote(
        self,
        interaction: discord.Interaction,
        option_id: str,
    ) -> None:
        try:
            result = await self.core.safari_route_application.cast_route_vote(
                self.guild_id,
                interaction.user.id,
                option_id,
            )
        except (
            SafariSessionNotFound,
            SafariRouteVoteNotFound,
            SafariRouteVoteUnavailable,
        ) as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        self.vote = result.vote
        await interaction.response.send_message(
            content=(
                f"Vote recorded for {result.option_id}"
                + (" (replaced)." if result.replaced else ".")
            ),
            ephemeral=True,
        )
        await self.refresh()

    async def resolve_route(self, interaction: discord.Interaction) -> None:
        try:
            result = await self.core.safari_route_application.resolve_route_vote(
                self.guild_id,
            )
        except (
            SafariSessionNotFound,
            SafariRouteVoteNotFound,
            SafariRouteVoteUnavailable,
        ) as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        self.session = result.session
        view = SafariEncounterView(
            core=self.core,
            guild_id=self.guild_id,
            session=result.session,
        )
        view.message = self.message
        file = await view.build_file()
        await interaction.response.edit_message(
            embed=view.build_embed(),
            view=view,
            attachments=[file],
        )

    async def refresh(self) -> None:
        if self.message is not None:
            await self.message.edit(
                embed=self.build_embed(),
                view=self,
            )

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True

        if self.message is not None:
            await self.message.edit(view=self)
