import discord


class ReleaseConfirmButton(discord.ui.Button):

    def __init__(
        self,
        core,
        trainer_id: int,
        collection_numbers: list[int],
    ):
        super().__init__(
            label="✅ Confirm",
            style=discord.ButtonStyle.success,
        )

        self._core = core
        self._trainer_id = trainer_id
        self._collection_numbers = collection_numbers

    async def callback(
        self,
        interaction: discord.Interaction,
    ):

        await interaction.response.defer()

        result = await self._core.release_application.release(
            trainer_id=self._trainer_id,
            collection_numbers=self._collection_numbers,
        )

        released = "\n".join(
            f"• #{creature.collection_number} {creature.species.name.title()}"
            for creature in result.released_creatures
        )

        emoji = {
            "normal": "⚪",
            "fire": "🔥",
            "water": "💧",
            "electric": "⚡",
            "grass": "🌿",
            "ice": "❄️",
            "fighting": "🥊",
            "poison": "☠️",
            "ground": "🌎",
            "flying": "🪽",
            "psychic": "🔮",
            "bug": "🐛",
            "rock": "🪨",
            "ghost": "👻",
            "dragon": "🐉",
            "dark": "🌑",
            "steel": "⚙️",
            "fairy": "🧚",
        }

        rewards = "\n".join(
            (
                f"• {emoji.get(candy_type.value, '🍬')} "
                f"{candy_type.value.title()} Candy ×{amount}"
            )
            for candy_type, amount in result.reward_bundle.items()
        )

        await interaction.edit_original_response(
            content=(
                "## Released\n\n"
                f"{released}\n\n"
                "## Rewards\n\n"
                f"{rewards}\n\n"
                "✅ Pokémon released successfully."
            ),
            view=None,
        )
