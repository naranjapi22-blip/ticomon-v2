from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from poke_env.battle import AbstractBattle
from poke_env.player import Player
from poke_env.player.battle_order import SingleBattleOrder
from poke_env.teambuilder import Teambuilder, TeambuilderPokemon

from application.pvp.models import (
    PvpAction,
    PvpActionKind,
    PvpLegalActions,
)
from core.creature.creature import Creature
from infrastructure.battle.poke_env.pvp_set_adapter import PvpSetAdapter

logger = logging.getLogger(__name__)

PVP_BATTLE_FORMAT = "gen9customgame"


@dataclass(frozen=True)
class PvpControllerCallbacks:
    on_actions: Callable[[int, PvpLegalActions], Awaitable[PvpAction]]
    on_protocol: Callable[[list[list[str]]], Awaitable[None]]
    on_finished: Callable[[AbstractBattle], Awaitable[None]]


class ManualPvpPlayer(Player):
    def __init__(
        self,
        trainer_id: int,
        team: str,
        callbacks: PvpControllerCallbacks,
        **kwargs: Any,
    ) -> None:
        self.trainer_id = trainer_id
        self._callbacks = callbacks
        super().__init__(
            battle_format=PVP_BATTLE_FORMAT,
            team=team,
            **kwargs,
        )

    def teampreview(self, battle: AbstractBattle) -> str:
        # The permanent order is the order selected in the private team picker.
        return "/team 1,2,3"

    async def choose_move(self, battle: AbstractBattle):
        actions, orders = self._legal_actions(battle)
        selected = await self._callbacks.on_actions(self.trainer_id, actions)
        try:
            return orders[selected.identifier]
        except KeyError as error:
            raise ValueError("Showdown returned an invalid PvP action.") from error

    async def _handle_battle_message(self, split_messages):
        await self._callbacks.on_protocol(split_messages)
        await super()._handle_battle_message(split_messages)

    def _battle_finished_callback(self, battle: AbstractBattle) -> None:
        asyncio.create_task(self._callbacks.on_finished(battle))

    @staticmethod
    def _legal_actions(
        battle: AbstractBattle,
    ) -> tuple[PvpLegalActions, dict[str, SingleBattleOrder]]:
        orders: dict[str, SingleBattleOrder] = {}
        moves: list[PvpAction] = []
        switches: list[PvpAction] = []
        for order in battle.valid_orders:
            if not isinstance(order, SingleBattleOrder):
                continue
            if hasattr(order.order, "id"):
                identifier = f"move:{order.order.id}"
                move = order.order
                pp = getattr(move, "current_pp", getattr(move, "pp", "?"))
                max_pp = getattr(move, "max_pp", getattr(move, "pp", "?"))
                action = PvpAction(
                    kind=PvpActionKind.MOVE,
                    identifier=identifier,
                    label=getattr(move, "name", move.id),
                    detail=f"PP {pp}/{max_pp}",
                )
                moves.append(action)
                orders[identifier] = order
            elif hasattr(order.order, "name"):
                identifier = f"switch:{order.order.name}"
                action = PvpAction(
                    kind=PvpActionKind.SWITCH,
                    identifier=identifier,
                    label=order.order.name,
                )
                switches.append(action)
                orders[identifier] = order

        forced_switch = bool(battle.force_switch)
        legal = PvpLegalActions(
            moves=tuple(moves),
            switches=tuple(switches),
            forced_switch=forced_switch,
        )
        return legal, orders


class PokeEnvPvpController:
    """Runs two manually controlled poke-env players against Showdown."""

    def __init__(
        self,
        set_adapter: PvpSetAdapter | None = None,
        player_factory: type[ManualPvpPlayer] = ManualPvpPlayer,
    ) -> None:
        self._set_adapter = set_adapter or PvpSetAdapter()
        self._player_factory = player_factory
        self._players: tuple[ManualPvpPlayer, ManualPvpPlayer] | None = None
        self._battle_task: asyncio.Task | None = None

    async def start(
        self,
        teams: dict[int, tuple[Creature, ...]],
        callbacks: PvpControllerCallbacks,
    ) -> None:
        player_ids = tuple(teams)
        if len(player_ids) != 2:
            raise ValueError("A PvP battle requires two teams.")
        packed_teams = {
            trainer_id: self._pack_team(team) for trainer_id, team in teams.items()
        }
        first = self._player_factory(
            player_ids[0], packed_teams[player_ids[0]], callbacks
        )
        second = self._player_factory(
            player_ids[1], packed_teams[player_ids[1]], callbacks
        )
        self._players = first, second
        self._battle_task = asyncio.create_task(first.battle_against(second))

    async def forfeit(self, trainer_id: int) -> None:
        if self._players is None:
            return
        for player in self._players:
            for battle in player.battles.values():
                if not battle.finished:
                    await player.ps_client.send_message("/forfeit", battle.battle_tag)
                    return

    async def close(self) -> None:
        if self._battle_task is not None and not self._battle_task.done():
            self._battle_task.cancel()
            await asyncio.gather(self._battle_task, return_exceptions=True)
        self._battle_task = None
        self._players = None

    def _pack_team(self, team: tuple[Creature, ...]) -> str:
        sets = []
        for creature in team:
            data = self._set_adapter.to_showdown_set(creature)
            sets.append(
                TeambuilderPokemon(
                    species=data.species,
                    ability=data.ability,
                    level=data.level,
                    evs=[0] * 6,
                    ivs=[
                        data.ivs[stat]
                        for stat in ("hp", "atk", "def", "spa", "spd", "spe")
                    ],
                    nature=data.nature,
                    moves=list(data.moves),
                    item=None,
                )
            )
        return Teambuilder.join_team(sets)
