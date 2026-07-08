import math

import discord

from application.bootstrap.core import CoreServices
from application.pokedex.filter import PokedexFilter
from interfaces.discord.files import image_to_discord_file
from rendering.pokedex.constants import POKEMON_PER_PAGE
from rendering.pokedex.renderer import PokedexRenderer


class PokedexView(discord.ui.View):
    def __init__(
        self,
        core: CoreServices,
        trainer_id: int,
        filter: PokedexFilter | None = None,
    ):
        super().__init__(timeout=300)

        self.core = core
        self.trainer_id = trainer_id

        self.page = 1
        self.total_pages = 1

        self.entries = ()

        self.renderer = PokedexRenderer()

        self.message: discord.Message | None = None

        self.filter = filter or PokedexFilter()

    async def initialize(self):
        """
        Loads the trainer's Pokédex once.
        """

        pokedex = await self.core.pokedex_service.get_pokedex(
            trainer_id=self.trainer_id,
        )

        entries = pokedex.entries

        if self.filter.discovered is not None:
            entries = tuple(
                entry for entry in entries if entry.discovered == self.filter.discovered
            )

        if self.filter.pokemon_type is not None:
            entries = tuple(
                entry
                for entry in entries
                if self.filter.pokemon_type.lower()
                in (pokemon_type.lower() for pokemon_type in entry.species.types)
            )

        if self.filter.generation is not None:
            entries = tuple(
                entry
                for entry in entries
                if (entry.species.metadata.generation == self.filter.generation)
            )

        if self.filter.legendary:
            entries = tuple(
                entry for entry in entries if entry.species.metadata.is_legendary
            )

        if self.filter.mythical:
            entries = tuple(
                entry for entry in entries if entry.species.metadata.is_mythical
            )

        # TODO:
        # Implement shiny filter once PokedexEntryDTO
        # exposes has_shiny.

        self.entries = entries

        self.total_pages = max(
            1,
            math.ceil(len(self.entries) / POKEMON_PER_PAGE),
        )

    async def _render_page(self):
        """
        Renders the current page.
        """

        image = self.renderer.render(
            self.entries,
            page=self.page,
        )

        file = image_to_discord_file(
            image,
            "pokedex.png",
        )

        title = "📖 Pokédex"

        if self.filter.discovered is True:
            title += " • Caught"

        elif self.filter.discovered is False:
            title += " • Missing"

        elif self.filter.pokemon_type is not None:
            title += f" • {self.filter.pokemon_type.title()}"

        elif self.filter.generation is not None:
            title += f" • Gen {self.filter.generation}"

        elif self.filter.legendary:
            title += " • Legendary"

        elif self.filter.mythical:
            title += " • Mythical"

        embed = discord.Embed(
            title=title,
            color=discord.Color.blurple(),
        )

        embed.set_image(
            url="attachment://pokedex.png",
        )

        self.previous.disabled = self.page == 1
        self.next.disabled = self.page == self.total_pages

        return embed, file

    @discord.ui.button(
        emoji="◀️",
        style=discord.ButtonStyle.secondary,
    )
    async def previous(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if self.page > 1:
            self.page -= 1

        embed, file = await self._render_page()

        await interaction.response.edit_message(
            embed=embed,
            attachments=[file],
            view=self,
        )

    @discord.ui.button(
        emoji="▶️",
        style=discord.ButtonStyle.secondary,
    )
    async def next(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if self.page < self.total_pages:
            self.page += 1

        embed, file = await self._render_page()

        await interaction.response.edit_message(
            embed=embed,
            attachments=[file],
            view=self,
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id != self.trainer_id:
            await interaction.response.send_message(
                "❌ This isn't your Pokédex.",
                ephemeral=True,
            )
            return False

        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

        if self.message is not None:
            await self.message.edit(
                view=self,
            )
