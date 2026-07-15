from pathlib import Path

import discord

from core.evolution.evolution_result import EvolutionResult
from rendering.evolution_animation import EvolutionAnimation

ASSETS_PATH = Path("rendering/assets")


def _build_animation(
    result: EvolutionResult,
):
    sprite_from = ASSETS_PATH / "regular" / f"{result.previous_species.id}.png"

    sprite_to = ASSETS_PATH / "regular" / f"{result.evolved_species.id}.png"

    animation = EvolutionAnimation(
        sprite_from=sprite_from,
        sprite_to=sprite_to,
        pokemon_from=result.previous_species.name.title(),
        pokemon_to=result.evolved_species.name.title(),
    )

    return discord.File(
        animation.gif_bytes(),
        filename="evolution.gif",
    )


async def send_evolution_result(
    send,
    result: EvolutionResult,
):
    await send(
        content=(
            "🎉 **Evolution successful!**\n"
            f"{result.previous_species.name.title()} "
            "➡️ "
            f"{result.evolved_species.name.title()}"
        ),
        file=_build_animation(result),
    )


async def edit_evolution_result(
    interaction: discord.Interaction,
    result: EvolutionResult,
):
    await interaction.response.edit_message(
        content="🎉 **Evolution successful!**",
        view=None,
    )

    await interaction.followup.send(
        file=_build_animation(result),
        content=(
            f"{result.previous_species.name.title()} "
            "➡️ "
            f"{result.evolved_species.name.title()}"
        ),
    )
