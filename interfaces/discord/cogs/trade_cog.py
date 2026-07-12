from datetime import UTC, datetime

import discord
from discord.ext import commands

from application.trade.exceptions import (
    TradeApplicationError,
    TradeCreatureNotFound,
    TradeCreatureNotOwned,
    TradeNotFound,
    TradeTrainerNotFound,
)
from core.trade.exceptions import (
    DuplicateTradeCreature,
    EmptyTradeOffer,
    InvalidTradeExpiry,
    InvalidTradeState,
    SameTradeParticipant,
    TradeError,
)


class TradeCog(commands.Cog):
    def __init__(self, core):
        self._core = core

    @commands.command(name="trade")
    async def trade(
        self,
        ctx: commands.Context,
        counterparty: discord.Member,
        *creature_ids: int,
    ):
        if not creature_ids:
            await ctx.send("You must provide at least one creature ID.")
            return

        try:
            trade = await self._core.trade_application.create_trade(
                initiator_trainer_id=ctx.author.id,
                counterparty_trainer_id=counterparty.id,
                initiator_creature_ids=list(creature_ids),
                created_at=datetime.now(UTC),
            )
        except (
            TradeTrainerNotFound,
            TradeCreatureNotFound,
            TradeCreatureNotOwned,
            TradeNotFound,
        ) as error:
            await ctx.send(f"Trade could not be created: {error}")
            return
        except (
            SameTradeParticipant,
            DuplicateTradeCreature,
            EmptyTradeOffer,
            InvalidTradeExpiry,
            InvalidTradeState,
        ):
            await ctx.send("Trade could not be created.")
            return
        except TradeApplicationError as error:
            await ctx.send(f"Trade could not be created: {error}")
            return
        except TradeError:
            await ctx.send("Trade could not be created.")
            return

        await ctx.send(f"Trade #{trade.id} created with {counterparty.mention}.")
