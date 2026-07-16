import asyncio
import logging
import math
from time import monotonic

import discord

from core.spawn.exceptions import NoActiveSpawnSession
from interfaces.discord.achievement_notifications import send_unlocks
from interfaces.discord.images import get_creature_gif, get_species_gif
from rendering.capture_animation import CaptureAnimation

logger = logging.getLogger(__name__)
_MISSING_CAPTURE_RESOURCES: set[tuple[int, int | None]] = set()


async def _capture_gif(creature, trainer, capture_ball: str):
    gif_url = get_creature_gif(creature)
    fallback_url = get_species_gif(
        creature.species.pokeapi_id,
        creature.is_shiny,
    )

    for index, sprite_url in enumerate(dict.fromkeys((gif_url, fallback_url))):
        try:
            animation = CaptureAnimation(
                sprite_path=sprite_url,
                pokemon_name=creature.species.name,
                trainer=trainer.gif.removesuffix(".gif"),
                pokeball=capture_ball,
                captured=True,
                type_name=creature.species.types[0],
            )
            return await asyncio.to_thread(animation.gif_bytes)
        except Exception:
            if index == 0:
                variant_id = (
                    creature.current_form.id
                    if creature.current_form is not None
                    else None
                )
                key = (creature.species.id, variant_id)
                if key not in _MISSING_CAPTURE_RESOURCES:
                    _MISSING_CAPTURE_RESOURCES.add(key)
                    logger.warning(
                        "capture_gif_resource_missing species_id=%s variant_id=%s "
                        "canonical_name=%s asset_key=%s",
                        creature.species.id,
                        variant_id,
                        (
                            f"{creature.species.name}:{creature.current_form.name}"
                            if creature.current_form is not None
                            else creature.species.name
                        ),
                        gif_url,
                    )

    return None


class CaptureButton(discord.ui.Button):
    COOLDOWN_SECONDS = 10
    _last_attempt: dict[int, float] = {}

    def __init__(self, core):
        super().__init__(
            label="🎯 Capture",
            style=discord.ButtonStyle.success,
        )

        self._core = core

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.defer()

        now = monotonic()

        last_attempt = self._last_attempt.get(interaction.user.id)

        if last_attempt is not None:
            remaining = self.COOLDOWN_SECONDS - (now - last_attempt)

            if remaining > 1:
                await interaction.followup.send(
                    (
                        f"⏳ Please wait "
                        f"{math.ceil(remaining)} seconds before trying again."
                    ),
                    ephemeral=True,
                )
                return

        try:
            result = await self._core.capture_application.capture(
                trainer_id=interaction.user.id,
                guild_id=interaction.guild.id,
            )
        except NoActiveSpawnSession:
            await interaction.followup.send(
                "❌ This encounter is no longer available.",
                ephemeral=True,
            )
            return

        # The attempt was valid; start the cooldown.
        self._last_attempt[interaction.user.id] = monotonic()

        ball_name = result.attempt.capture_ball.name.replace(
            "_",
            " ",
        ).title()

        if not result.success:
            await interaction.followup.send(
                content=(
                    f"❌ You failed to catch the Pokémon.\n"
                    f"🎯 Capture Chance: {result.attempt.chance * 100:.2f}%"
                ),
                ephemeral=True,
            )
            return

        trainer = await self._core.profile_service.get_selected_trainer(
            interaction.user.id,
        )

        gif = await _capture_gif(
            result.creature,
            trainer,
            result.attempt.capture_ball.name,
        )

        rewards = "\n".join(
            f"🍬 {candy_type.value.title()}: +{amount}"
            for candy_type, amount in result.reward.items()
        )

        message = {
            "content": (
                f"🎉 {interaction.user.mention} caught "
                f"{result.creature.species.name.title()} "
                f"(#{result.creature.collection_number}) "
                f"using a {ball_name}!\n"
                f"🎯 Capture Chance: {result.attempt.chance * 100:.2f}%\n\n"
                f"{rewards}"
            )
        }
        if gif is not None:
            message["file"] = discord.File(gif, filename="capture.gif")

        await interaction.followup.send(
            **message,
        )

        await send_unlocks(
            interaction.followup.send,
            result.achievements,
            context=f"capture_button trainer_id={interaction.user.id}",
        )

        await interaction.delete_original_response()
