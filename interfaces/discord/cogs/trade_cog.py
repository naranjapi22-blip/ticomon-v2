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
from interfaces.discord.views.trade_view import TradeView


class TradeCog(commands.Cog):
    def __init__(self, core):
        self._core = core

    @commands.command(name="trade")
    async def trade(
        self,
        ctx: commands.Context,
        counterparty: discord.Member,
        collection_number: int,
    ) -> None:
        try:
            trade = (
                await self._core.trade_application.create_trade_from_collection_number(
                    initiator_trainer_id=ctx.author.id,
                    counterparty_trainer_id=counterparty.id,
                    initiator_collection_number=collection_number,
                    created_at=datetime.now(UTC),
                )
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

        trade_display = await self._core.trade_display_service.get_trade_display(
            trade.id,
        )

        view = TradeView(
            self._core,
            trade_display,
        )

        message = await ctx.send(
            embed=view.build_embed(),
            view=view,
        )

        view.message = message
