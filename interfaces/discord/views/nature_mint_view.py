import discord

from core.creature.nature import Nature
from core.creature.stat import Stat

_STAT_LABELS = {
    Stat.ATTACK: "Attack",
    Stat.DEFENSE: "Defense",
    Stat.SP_ATTACK: "Special Attack",
    Stat.SP_DEFENSE: "Special Defense",
    Stat.SPEED: "Speed",
}


def _effect_text(nature: Nature) -> str:
    increased, decreased = nature.effect()
    if increased is None:
        return "Neutral effect"
    return f"+{_STAT_LABELS[increased]} / -{_STAT_LABELS[decreased]}"


class NatureMintView(discord.ui.View):
    def __init__(self, core, trainer_id: int, collection_number: int, preview) -> None:
        super().__init__(timeout=120)
        self.core = core
        self.trainer_id = trainer_id
        self.collection_number = collection_number
        self.preview = preview
        self.increased: Stat | None = None
        self.decreased: Stat | None = None
        self._show_start()

    @property
    def creature(self):
        return self.preview.creature

    def _embed(self, description: str) -> discord.Embed:
        creature = self.creature
        return discord.Embed(
            title=(
                f"Nature Mint — {creature.species.name.title()} "
                f"(#{creature.collection_number})"
            ),
            description=description,
            color=discord.Color.green(),
        )

    def _show_start(self) -> None:
        self.clear_items()
        self.add_item(_UseMintButton())
        self.add_item(_CancelMintButton())

    def _show_selector(self) -> None:
        self.clear_items()
        self.add_item(_IncreasedSelect(self))
        self.add_item(_RestoreButton())
        self.add_item(_CancelMintButton())

    def _show_decreased(self) -> None:
        self.clear_items()
        self.add_item(_DecreasedSelect(self))
        self.add_item(_CancelMintButton())

    def _show_final(self, nature: Nature | None) -> discord.Embed:
        self.clear_items()
        self.add_item(_ConfirmMintButton(self))
        self.add_item(_BackMintButton(self))
        self.add_item(_CancelMintButton())
        if nature is None:
            effect = _effect_text(self.creature.nature)
            equivalent = str(self.creature.nature)
        else:
            effect = _effect_text(nature)
            equivalent = str(nature)
        return self._embed(
            f"Apply this effect?\n\n{effect}\n"
            f"Equivalent nature: **{equivalent}**\n"
            "Cost: **1 Nature Mint**\n"
            f"Remaining after use: **{self.preview.mint_amount - 1}**"
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.trainer_id:
            await interaction.response.send_message(
                "This Nature Mint view belongs to another trainer.", ephemeral=True
            )
            return False
        return True


class _UseMintButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Use Mint", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        view._show_selector()
        await interaction.response.edit_message(
            embed=view._embed("Choose the increased statistic."), view=view
        )


class _CancelMintButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Cancel", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction) -> None:
        for child in self.view.children:
            child.disabled = True
        await interaction.response.edit_message(
            content="Nature Mint use cancelled. No Nature Mint was consumed.",
            embed=None,
            view=self.view,
        )


class _IncreasedSelect(discord.ui.Select):
    def __init__(self, view: NatureMintView) -> None:
        super().__init__(
            placeholder="Increased stat",
            options=[
                discord.SelectOption(label=label, value=stat.value)
                for stat, label in _STAT_LABELS.items()
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        view.increased = Stat(self.values[0])
        view._show_decreased()
        await interaction.response.edit_message(
            embed=view._embed(
                f"Increased: **{_STAT_LABELS[view.increased]}**\n"
                "Choose the reduced statistic."
            ),
            view=view,
        )


class _DecreasedSelect(discord.ui.Select):
    def __init__(self, view: NatureMintView) -> None:
        options = []
        for stat, label in _STAT_LABELS.items():
            if stat is view.increased:
                continue
            try:
                nature = Nature.from_effect(view.increased, stat)
            except ValueError:
                continue
            options.append(
                discord.SelectOption(
                    label=label, value=stat.value, description=str(nature)
                )
            )
        super().__init__(placeholder="Reduced stat", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        view.decreased = Stat(self.values[0])
        nature = Nature.from_effect(view.increased, view.decreased)
        await interaction.response.edit_message(
            embed=view._show_final(nature), view=view
        )


class _RestoreButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Restore original", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        view.increased = None
        view.decreased = None
        await interaction.response.edit_message(embed=view._show_final(None), view=view)


class _BackMintButton(discord.ui.Button):
    def __init__(self, view: NatureMintView) -> None:
        super().__init__(label="Back", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        view._show_selector()
        await interaction.response.edit_message(
            embed=view._embed("Choose an effect."), view=view
        )


class _ConfirmMintButton(discord.ui.Button):
    def __init__(self, view: NatureMintView) -> None:
        super().__init__(label="Confirm", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        try:
            result = await view.core.nature_mint_application.apply(
                view.trainer_id,
                view.collection_number,
                view.increased,
                view.decreased,
            )
        except ValueError as error:
            await interaction.response.edit_message(
                embed=view._embed(str(error)), view=view
            )
            return
        for child in view.children:
            child.disabled = True
        creature = result.creature
        await interaction.response.edit_message(
            embed=view._embed(
                f"**{creature.species.name.title()} (#{creature.collection_number})** "
                f"now has the **{creature.effective_nature}** effect.\n\n"
                f"Original nature: **{creature.nature}**\n"
                f"Current effect: {_effect_text(creature.effective_nature)}\n"
                f"Nature Mints remaining: **{result.remaining_mints}**"
            ),
            view=view,
        )
