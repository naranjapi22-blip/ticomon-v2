"""Run a small two-player PvP smoke test against a local Showdown server."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from poke_env.battle import AbstractBattle
from poke_env.player import Player
from poke_env.ps_client import ServerConfiguration
from poke_env.teambuilder import Teambuilder, TeambuilderPokemon

from application.pvp.snapshots import PvpBattleSnapshot, snapshot_battle
from infrastructure.battle.poke_env.pvp_controller import PVP_BATTLE_FORMAT

SHOWDOWN_WEBSOCKET_URL = os.getenv(
    "SHOWDOWN_WEBSOCKET_URL", "ws://localhost:8000/showdown/websocket"
)
SHOWDOWN_AUTHENTICATION_URL = os.getenv(
    "SHOWDOWN_AUTHENTICATION_URL", "http://localhost:8000/action.php?"
)


def _team() -> str:
    sets = []
    for species, ability, moves in (
        ("Pikachu", "static", ["Thunderbolt", "Quick Attack"]),
        ("Eevee", "runaway", ["Tackle", "Quick Attack"]),
        ("Raichu", "static", ["Thunderbolt", "Quick Attack"]),
    ):
        sets.append(
            TeambuilderPokemon(
                species=species,
                ability=ability,
                level=50,
                evs=[0] * 6,
                ivs=[31] * 6,
                nature="Hardy",
                moves=moves,
                item=None,
            )
        )
    return Teambuilder.join_team(sets)


@dataclass
class DiagnosticResult:
    snapshots: list[PvpBattleSnapshot]
    battle_finished: bool


class DiagnosticPlayer(Player):
    def __init__(self, trainer_id: int, team: str, **kwargs) -> None:
        self.trainer_id = trainer_id
        self.opponent_id = 0
        self.snapshots: list[PvpBattleSnapshot] = []
        super().__init__(
            battle_format=PVP_BATTLE_FORMAT,
            team=team,
            **kwargs,
        )

    def teampreview(self, battle: AbstractBattle) -> str:
        return "/team 1,2,3"

    async def choose_move(self, battle: AbstractBattle):
        for order in battle.valid_orders:
            if hasattr(order, "order") and hasattr(order.order, "id"):
                return order
        return self.choose_random_move(battle)

    async def _handle_battle_message(self, split_messages):
        await super()._handle_battle_message(split_messages)
        for battle in self.battles.values():
            self.snapshots.append(
                snapshot_battle(
                    battle,
                    player_id=self.trainer_id,
                    opponent_id=self.opponent_id,
                )
            )


async def run_diagnostic() -> DiagnosticResult:
    configuration = ServerConfiguration(
        websocket_url=SHOWDOWN_WEBSOCKET_URL,
        authentication_url=SHOWDOWN_AUTHENTICATION_URL,
    )
    player_one = DiagnosticPlayer(
        1,
        _team(),
        loop=asyncio.get_running_loop(),
        server_configuration=configuration,
    )
    player_two = DiagnosticPlayer(
        2,
        _team(),
        loop=asyncio.get_running_loop(),
        server_configuration=configuration,
    )
    player_one.opponent_id = 2
    player_two.opponent_id = 1
    battle_task = None
    try:
        await asyncio.wait_for(
            asyncio.gather(
                player_one.ps_client.logged_in.wait(),
                player_two.ps_client.logged_in.wait(),
            ),
            timeout=10,
        )
        battle_task = asyncio.create_task(player_one.battle_against(player_two))
        await asyncio.wait_for(battle_task, timeout=60)
        snapshots = player_one.snapshots + player_two.snapshots
        return DiagnosticResult(
            snapshots, any(snapshot.finished for snapshot in snapshots)
        )
    finally:
        if battle_task is not None and not battle_task.done():
            battle_task.cancel()
            await asyncio.gather(battle_task, return_exceptions=True)
        await asyncio.gather(
            player_one.ps_client.stop_listening(),
            player_two.ps_client.stop_listening(),
            return_exceptions=True,
        )


async def main() -> None:
    result = await run_diagnostic()
    if not result.snapshots:
        raise RuntimeError("Showdown completed without producing a battle snapshot.")
    latest = max(
        result.snapshots, key=lambda snapshot: (snapshot.finished, snapshot.turn)
    )
    print(
        f"snapshots={len(result.snapshots)} turn={latest.turn} "
        f"finished={result.battle_finished}"
    )


if __name__ == "__main__":
    asyncio.run(main())
