from discord.ext import commands

from infrastructure.battle.poke_env.loadout_catalog import PokeEnvLoadoutCatalog


class MovesCog(commands.Cog):
    """Displays and edits a creature's persistent PvP moveset."""

    def __init__(self, core) -> None:
        self._core = core
        self._catalog = PokeEnvLoadoutCatalog()

    @commands.command(name="moves")
    async def moves(
        self,
        ctx,
        collection_number: int,
        slot: int | None = None,
        move: str | None = None,
    ) -> None:
        if self._core.pvp_application_service.registry.is_occupied(ctx.author.id):
            await ctx.send("You cannot edit moves during an active PvP challenge.")
            return
        try:
            creature = await self._core.creature_repository.get_by_collection_number(
                ctx.author.id, collection_number
            )
        except ValueError:
            await ctx.send("Creature not found.")
            return

        legal_moves = {
            item.id: item for item in self._catalog.moves_for(creature.species)
        }
        if slot is not None or move is not None:
            if slot is None or move is None or slot not in range(1, 5):
                await ctx.send("A slot from 1 to 4 and a legal move are required.")
                return
            move_id = move.strip().lower().replace(" ", "-")
            if move_id not in legal_moves:
                await ctx.send("That move is not legal for this creature.")
                return
            equipped = list(creature.moves)
            while len(equipped) < 4:
                equipped.append("")
            if move_id in equipped and equipped[slot - 1] != move_id:
                await ctx.send("A creature cannot equip duplicate moves.")
                return
            equipped[slot - 1] = move_id
            creature.moves = tuple(item for item in equipped if item)
            await self._core.creature_repository.update(creature)

        lines = []
        for index, move_id in enumerate(creature.moves, start=1):
            data = legal_moves.get(move_id)
            if data is None:
                lines.append(f"{index}. {move_id} (not in the current catalog)")
                continue
            power = data.base_power if data.base_power is not None else "—"
            accuracy = data.accuracy if data.accuracy is not None else "—"
            lines.append(
                f"{index}. **{data.display_name}** — {data.move_type.title()} · "
                f"{data.category} · Power {power} · Accuracy {accuracy} · "
                f"PP {data.pp}"
            )
        await ctx.send(
            f"**#{collection_number} {creature.species.name} moves**\n"
            + ("\n".join(lines) if lines else "No moves equipped.")
        )

    @moves.error
    async def moves_error(self, ctx, error) -> None:
        if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            await ctx.send("Usage: !moves <collection> [slot] [move]")
            return
        raise error
