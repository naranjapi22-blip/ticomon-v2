from __future__ import annotations

from interfaces.discord.views.battle_selection_view import BattleChallengeView


class BattleGifChallengeView(BattleChallengeView):
    async def refresh_display(self, battle) -> None:
        if self.message is None:
            return

        if battle.is_ready:
            from interfaces.discord.views.battle_gif_arena_view import (
                BattleGifArenaView,
            )

            arena_view = BattleGifArenaView(
                self.core,
                self.battle_id,
                self.initiator_id,
                self.opponent_id,
            )
            arena_view.message = self.message
            await self.message.edit(
                embed=arena_view.build_embed(battle),
                view=arena_view,
            )
            self.stop()
            return

        await self.message.edit(embed=self.build_embed(battle), view=self)
