import logging
from pathlib import Path

import discord

from core.evolution.evolution_result import EvolutionResult
from interfaces.discord.achievement_notifications import format_unlocks
from interfaces.discord.application_emojis import get_application_emojis
from rendering.evolution_animation import EvolutionAnimation

ASSETS_PATH = Path("rendering/assets")
logger = logging.getLogger(__name__)


def _achievement_text(result, emoji_index=None) -> str:
    achievements = getattr(result, "achievements", ())
    if not achievements:
        return ""
    try:
        return f"\n\n{format_unlocks(achievements, emoji_index)}"
    except Exception:
        logger.exception("evolution achievement notification failed")
        return ""


def _build_animation(result: EvolutionResult) -> discord.File | None:
    try:
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
    except Exception:
        logger.exception("evolution animation creation failed")
        return None


def _result_content(result, emoji_index=None) -> str:
    return (
        "🎉 **Evolution successful!**\n"
        f"{result.previous_species.name.title()} "
        "➡️ "
        f"{result.evolved_species.name.title()}"
        f"{_achievement_text(result, emoji_index)}"
    )


async def send_evolution_result(send, result: EvolutionResult, bot=None):
    result_file = _build_animation(result)
    emoji_index = await get_application_emojis(bot) if bot is not None else {}
    kwargs = {"content": _result_content(result, emoji_index)}
    if result_file is not None:
        kwargs["file"] = result_file
    await send(**kwargs)


async def edit_evolution_result(
    interaction: discord.Interaction,
    result: EvolutionResult,
):
    result_file = _build_animation(result)
    emoji_index = await get_application_emojis(interaction.client)
    attachments = [result_file] if result_file is not None else []
    await interaction.edit_original_response(
        content=_result_content(result, emoji_index),
        attachments=attachments,
        view=None,
    )
