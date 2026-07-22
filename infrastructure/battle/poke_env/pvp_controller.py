from __future__ import annotations

import asyncio
import logging
import os
import re
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from poke_env.battle import AbstractBattle
from poke_env.exceptions import ShowdownException
from poke_env.player import Player
from poke_env.player.battle_order import SingleBattleOrder
from poke_env.ps_client import ServerConfiguration
from poke_env.ps_client.account_configuration import AccountConfiguration
from poke_env.teambuilder import Teambuilder, TeambuilderPokemon
from websockets.exceptions import ConnectionClosedOK

from application.pvp.models import (
    PvpAction,
    PvpActionKind,
    PvpLegalActions,
)
from application.pvp.snapshots import PvpBattleSnapshot, snapshot_battle
from application.pvp.task_management import (
    cancel_task_safely,
    cancel_tasks_safely,
    register_task,
    unique_pending_tasks,
)
from core.creature.creature import Creature
from infrastructure.battle.poke_env.pvp_set_adapter import PvpSetAdapter
from rendering.battle.pvp_sprite_urls import showdown_sprite_identifier
from rendering.sprites import get_capture_creature_gif

logger = logging.getLogger(__name__)


class _ExpectedCancellationFilter(logging.Filter):
    """Suppress poke-env's critical cancellation message only during close."""

    def __init__(self, player) -> None:
        super().__init__()
        self._player = player

    def filter(self, record: logging.LogRecord) -> bool:
        return not (
            getattr(self._player, "_closing", False)
            and record.getMessage().startswith("CancelledError intercepted")
        )


PVP_BATTLE_FORMAT = "gen9customgame"
SHOWDOWN_CONNECTION_TIMEOUT_SECONDS = 10
SHOWDOWN_START_TIMEOUT_SECONDS = 15
SHOWDOWN_CLOSE_TIMEOUT_SECONDS = 5
SHOWDOWN_MESSAGE_CLOSE_TIMEOUT_SECONDS = 1
SHOWDOWN_WEBSOCKET_URL = os.getenv(
    "SHOWDOWN_WEBSOCKET_URL", "ws://localhost:8000/showdown/websocket"
)
SHOWDOWN_AUTHENTICATION_URL = os.getenv("SHOWDOWN_AUTHENTICATION_URL", "")
DEFAULT_SHOWDOWN_WEBSOCKET_URL = "ws://localhost:8000/showdown/websocket"


def _safe_exception_message(error: BaseException) -> str:
    message = str(error).replace("\r", " ").replace("\n", " ").strip()
    for secret_name in (
        "DISCORD_TOKEN",
        "NEON_DATABASE_URL",
        "SHOWDOWN_WEBSOCKET_URL",
        "SHOWDOWN_AUTHENTICATION_URL",
    ):
        secret = os.getenv(secret_name)
        if secret:
            message = message.replace(secret, "[REDACTED]")
    message = re.sub(
        r"(?i)(authorization|password|secret|token)(\s*[:=]\s*)\S+",
        r"\1\2[REDACTED]",
        message,
    )
    message = re.sub(
        r"(?i)(https?://)([^/\s:@]+):([^@\s]+)@",
        r"\1[REDACTED]@",
        message,
    )
    return message[:500] or "<no exception message>"


def _showdown_urls() -> tuple[str, str]:
    return (
        os.getenv("SHOWDOWN_WEBSOCKET_URL", SHOWDOWN_WEBSOCKET_URL),
        os.getenv("SHOWDOWN_AUTHENTICATION_URL", SHOWDOWN_AUTHENTICATION_URL),
    )


def _validate_url(url: str, *, schemes: set[str], setting_name: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in schemes:
        expected = " or ".join(sorted(schemes))
        raise RuntimeError(f"{setting_name} must use {expected}.")
    if not parsed.hostname:
        raise RuntimeError(f"{setting_name} must include a hostname.")


def validate_showdown_configuration() -> tuple[str, str]:
    websocket_url, authentication_url = _showdown_urls()
    if not websocket_url:
        raise RuntimeError(
            "PvP Showdown is not configured: set SHOWDOWN_WEBSOCKET_URL."
        )
    if (
        not os.getenv("SHOWDOWN_WEBSOCKET_URL")
        and websocket_url == DEFAULT_SHOWDOWN_WEBSOCKET_URL
    ):
        raise RuntimeError(
            "PvP Showdown is not configured: set SHOWDOWN_WEBSOCKET_URL. The default "
            "localhost URLs are only valid when a local Showdown server is "
            "running."
        )
    _validate_url(
        websocket_url,
        schemes={"ws", "wss"},
        setting_name="SHOWDOWN_WEBSOCKET_URL",
    )
    if authentication_url:
        _validate_url(
            authentication_url,
            schemes={"http", "https"},
            setting_name="SHOWDOWN_AUTHENTICATION_URL",
        )
    return websocket_url, authentication_url


@dataclass(frozen=True)
class PvpControllerCallbacks:
    on_actions: Callable[[int, PvpLegalActions], Awaitable[PvpAction]]
    on_protocol: Callable[[int, list[list[str]]], Awaitable[None]]
    on_finished: Callable[[AbstractBattle], Awaitable[None]]
    on_snapshot: Callable[[PvpBattleSnapshot], Awaitable[None]] | None = None
    on_error: Callable[[BaseException], Awaitable[None]] | None = None


class ManualPvpPlayer(Player):
    def __init__(
        self,
        trainer_id: int,
        team: str,
        callbacks: PvpControllerCallbacks,
        username: str,
        callback_tasks: set[asyncio.Task] | None = None,
        capture_sprite_urls: dict[tuple[str, bool], str] | None = None,
        **kwargs: Any,
    ) -> None:
        self.trainer_id = trainer_id
        self.opponent_id: int | None = None
        self._callbacks = callbacks
        self._callback_tasks = callback_tasks
        self._capture_sprite_urls = capture_sprite_urls or {}
        self._pokeapi_ids = kwargs.pop("pokeapi_ids", {})
        self._closing = False
        self.background_errors: list[BaseException] = []
        self._pending_finished_battles: list[AbstractBattle] = []
        self._finished_battle_ids: set[int] = set()
        super().__init__(
            account_configuration=AccountConfiguration(username, None),
            battle_format=PVP_BATTLE_FORMAT,
            team=team,
            **kwargs,
        )
        self.ps_client.change_avatar = self._skip_avatar_change
        self.ps_client.logger.addFilter(_ExpectedCancellationFilter(self))
        original_handle_message = self.ps_client._handle_message

        async def _handle_message_without_challenge_logging(message):
            if "|nametaken|" in message:
                raise ShowdownException("Showdown rejected the generated username.")
            await original_handle_message(message)

        self.ps_client._handle_message = _handle_message_without_challenge_logging
        self.ps_client._active_tasks = _RetrievedTaskSet(self)

    async def _skip_avatar_change(self, _avatar) -> None:
        return

    def _record_background_error(self, error: BaseException) -> None:
        self.background_errors.append(error)

    def _schedule_callback(self, coroutine) -> None:
        task = register_task(
            asyncio.create_task(
                coroutine, name=f"pvp-player-callback:{self.trainer_id}"
            ),
            owner="PokeEnvPvpController",
            role="final_callback",
            may_call_cleanup=True,
            cleanup_may_cancel=False,
        )
        if self._callback_tasks is None:
            task.add_done_callback(_consume_task_exception)
            return
        self._callback_tasks.add(task)
        task.add_done_callback(self._callback_tasks.discard)
        task.add_done_callback(_consume_task_exception)

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
        await self._callbacks.on_protocol(self.trainer_id, split_messages)
        try:
            await super()._handle_battle_message(split_messages)
        except ConnectionClosedOK:
            if not any(
                getattr(battle, "finished", False) for battle in self.battles.values()
            ):
                raise
            logger.debug(
                "Showdown socket closed normally after battle completion "
                "trainer_id=%s",
                self.trainer_id,
            )
        for battle in self.battles.values():
            if self._callbacks.on_snapshot is not None:
                await self._callbacks.on_snapshot(
                    snapshot_battle(
                        battle,
                        player_id=self.trainer_id,
                        opponent_id=self.opponent_id or 0,
                        capture_sprite_urls=self._capture_sprite_urls,
                        pokeapi_ids=self._pokeapi_ids,
                    )
                )
            if battle.finished and id(battle) not in self._finished_battle_ids:
                self._finished_battle_ids.add(id(battle))
                if battle in self._pending_finished_battles:
                    self._pending_finished_battles.remove(battle)
                self._schedule_callback(self._callbacks.on_finished(battle))

    def _battle_finished_callback(self, battle: AbstractBattle) -> None:
        self._pending_finished_battles.append(battle)

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
                if isinstance(pp, (int, float)) and pp <= 0:
                    continue
                action = PvpAction(
                    kind=PvpActionKind.MOVE,
                    identifier=identifier,
                    label=getattr(move, "name", move.id),
                    detail=f"PP {pp}/{max_pp}",
                    move_type=_display_value(getattr(move, "type", None)),
                    category=_display_value(getattr(move, "category", None)),
                    power=_numeric_value(getattr(move, "base_power", None)),
                    accuracy=_accuracy_percent(getattr(move, "accuracy", None)),
                )
                moves.append(action)
                orders[identifier] = order
            elif hasattr(order.order, "name"):
                identifier = f"switch:{order.order.name}"
                if bool(getattr(order.order, "fainted", False)):
                    continue
                active = getattr(battle, "active_pokemon", None)
                if active is not None and order.order.name == getattr(
                    active, "species", None
                ):
                    continue
                action = PvpAction(
                    kind=PvpActionKind.SWITCH,
                    identifier=identifier,
                    label=order.order.name,
                    hp_current=getattr(order.order, "current_hp", None),
                    hp_max=getattr(order.order, "max_hp", None),
                    status=_display_value(getattr(order.order, "status", None)),
                    fainted=bool(getattr(order.order, "fainted", False)),
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


def _display_value(value) -> str | None:
    if value is None:
        return None
    return str(getattr(value, "name", value)).replace("_", " ").title()


def _numeric_value(value) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _accuracy_percent(value) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if 0 <= numeric <= 1 and isinstance(value, float):
        return round(numeric * 100)
    if 0 <= numeric <= 100:
        return round(numeric)
    return None


class PokeEnvPvpController:
    """Runs two manually controlled poke-env players against Showdown."""

    def __init__(
        self,
        set_adapter: PvpSetAdapter | None = None,
        player_factory: type[ManualPvpPlayer] = ManualPvpPlayer,
        session_token: str | None = None,
    ) -> None:
        self._set_adapter = set_adapter or PvpSetAdapter()
        self._player_factory = player_factory
        self._session_token = session_token or secrets.token_hex(8)
        self._players: tuple[ManualPvpPlayer, ManualPvpPlayer] | None = None
        self._battle_task: asyncio.Task | None = None
        self._callback_tasks: set[asyncio.Task] = set()
        self._callbacks: PvpControllerCallbacks | None = None
        self._attempt = 0
        self._player_usernames: dict[str, int] = {}

    async def start(
        self,
        teams: dict[int, tuple[Creature, ...]],
        callbacks: PvpControllerCallbacks,
    ) -> None:
        self._callbacks = callbacks
        websocket_url, authentication_url = validate_showdown_configuration()
        player_ids = tuple(teams)
        if len(player_ids) != 2:
            raise ValueError("A PvP battle requires two teams.")
        packed_teams = {
            trainer_id: self._pack_team(team) for trainer_id, team in teams.items()
        }
        capture_sprite_urls = self._capture_sprite_urls(teams)
        pokeapi_ids = self._pokeapi_ids(teams)
        player_kwargs = {
            "callbacks": callbacks,
            "loop": asyncio.get_running_loop(),
            "server_configuration": ServerConfiguration(
                websocket_url=websocket_url,
                authentication_url=authentication_url,
            ),
            "capture_sprite_urls": capture_sprite_urls,
            "pokeapi_ids": pokeapi_ids,
        }
        last_error = None
        for attempt in range(1, 4):
            self._attempt = attempt
            first = self._make_player(
                player_ids[0], packed_teams[player_ids[0]], player_kwargs, 1
            )
            second = self._make_player(
                player_ids[1], packed_teams[player_ids[1]], player_kwargs, 2
            )
            first.opponent_id = player_ids[1]
            second.opponent_id = player_ids[0]
            self._players = first, second
            try:
                await asyncio.wait_for(
                    self._wait_for_login(first, second),
                    timeout=SHOWDOWN_CONNECTION_TIMEOUT_SECONDS,
                )
                self._battle_task = register_task(
                    asyncio.create_task(
                        first.battle_against(second),
                        name=f"pvp-battle:{player_ids[0]}:{player_ids[1]}",
                    ),
                    owner="PokeEnvPvpController",
                    role="battle",
                )
                self._battle_task.add_done_callback(self._battle_task_finished)
                await asyncio.sleep(0)
                return
            except Exception as error:
                last_error = error
                logger.warning(
                    "Retrying PvP Showdown login attempt=%s error_type=%s error=%s",
                    attempt,
                    type(error).__name__,
                    _safe_exception_message(error),
                    exc_info=(type(error), error, error.__traceback__),
                )
                await self.close()
        raise TimeoutError(
            "PvP Showdown login did not complete after retries."
        ) from last_error

    def _battle_task_finished(self, task: asyncio.Task) -> None:
        if task.cancelled():
            return
        error = task.exception()
        if error is None or self._callbacks is None or self._callbacks.on_error is None:
            _consume_task_exception(task)
            return
        logger.warning(
            "PvP Showdown battle task failed attempt=%s error_type=%s error=%s",
            self._attempt,
            type(error).__name__,
            _safe_exception_message(error),
            exc_info=(type(error), error, error.__traceback__),
        )
        callback_task = register_task(
            asyncio.create_task(
                self._callbacks.on_error(error),
                name=f"pvp-controller-error:{self._attempt}",
            ),
            owner="PokeEnvPvpController",
            role="final_callback",
            may_call_cleanup=True,
            cleanup_may_cancel=False,
        )
        self._callback_tasks.add(callback_task)
        callback_task.add_done_callback(self._callback_tasks.discard)
        callback_task.add_done_callback(_consume_task_exception)

    def _make_player(self, trainer_id, team, player_kwargs, side):
        username = f"tm{self._session_token[:10]}a{self._attempt}p{side}"
        self._player_usernames[username.casefold()] = trainer_id
        return self._player_factory(
            trainer_id,
            team,
            username=username,
            callback_tasks=self._callback_tasks,
            **player_kwargs,
        )

    def resolve_winner(self, username: str | None) -> int | None:
        if not username:
            return None
        return self._player_usernames.get(str(username).strip().casefold())

    async def _wait_for_login(self, first, second) -> None:
        while not (
            first.ps_client.logged_in.is_set() and second.ps_client.logged_in.is_set()
        ):
            for player in (first, second):
                if getattr(player, "background_errors", None):
                    raise player.background_errors[0]
            await asyncio.sleep(0.05)

    async def forfeit(self, trainer_id: int) -> None:
        if self._players is None:
            return
        for player in self._players:
            for battle in player.battles.values():
                if not battle.finished:
                    await player.ps_client.send_message("/forfeit", battle.battle_tag)
                    return

    async def close(self) -> None:
        current_task = asyncio.current_task()
        players = self._players
        if players is not None:
            for player in players:
                player._closing = True
        if self._battle_task is not None:
            if self._battle_task is current_task:
                logger.warning(
                    "Skipping task owned by current final-delivery path "
                    "task=%s reason=self_battle_close",
                    current_task.get_name() if current_task is not None else None,
                )
            elif not self._battle_task.done():
                try:
                    await asyncio.wait_for(
                        asyncio.shield(self._battle_task),
                        timeout=SHOWDOWN_CLOSE_TIMEOUT_SECONDS,
                    )
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    await cancel_task_safely(
                        self._battle_task,
                        current_task=current_task,
                        owner="PokeEnvPvpController",
                        reason="controller close battle task",
                    )
            else:
                try:
                    self._battle_task.result()
                except asyncio.CancelledError:
                    pass
                except Exception:
                    logger.debug("PvP Showdown task ended with an error", exc_info=True)
        if players is not None:
            for player in players:
                try:
                    await asyncio.wait_for(
                        player.ps_client.stop_listening(),
                        timeout=SHOWDOWN_CLOSE_TIMEOUT_SECONDS,
                    )
                except asyncio.CancelledError:
                    if not player._closing:
                        raise
                    logger.debug("PvP Showdown listener cancellation during close")
                except Exception:
                    logger.debug("Unable to close a PvP Showdown player", exc_info=True)
        if players is not None:
            active_tasks = unique_pending_tasks(
                (
                    task
                    for player in players
                    for task in list(getattr(player.ps_client, "_active_tasks", ()))
                ),
                current_task=current_task,
            )
            if active_tasks:
                _, pending_tasks = await asyncio.wait(
                    active_tasks, timeout=SHOWDOWN_MESSAGE_CLOSE_TIMEOUT_SECONDS
                )
                await cancel_tasks_safely(
                    pending_tasks,
                    current_task=current_task,
                    owner="PokeEnvPvpController",
                    reason="controller close player listeners",
                )
        callback_tasks = unique_pending_tasks(
            self._callback_tasks, current_task=current_task
        )
        if callback_tasks:
            _, pending_tasks = await asyncio.wait(
                callback_tasks, timeout=SHOWDOWN_MESSAGE_CLOSE_TIMEOUT_SECONDS
            )
            await cancel_tasks_safely(
                pending_tasks,
                current_task=current_task,
                owner="PokeEnvPvpController",
                reason="controller close callback tasks",
            )
            self._callback_tasks.clear()
        if current_task is not None:
            self._callback_tasks.discard(current_task)
        self._battle_task = None
        self._players = None
        self._attempt = 0
        self._callbacks = None
        self._player_usernames.clear()

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

    def _capture_sprite_urls(
        self, teams: dict[int, tuple[Creature, ...]]
    ) -> dict[tuple[str, bool], str]:
        urls: dict[tuple[str, bool], str] = {}
        for team in teams.values():
            for creature in team:
                data = self._set_adapter.to_showdown_set(creature)
                identifier = showdown_sprite_identifier(
                    data.species,
                    creature.current_form.name if creature.current_form else None,
                )
                urls[(identifier, creature.is_shiny)] = get_capture_creature_gif(
                    creature
                )
        return urls

    def _pokeapi_ids(
        self, teams: dict[int, tuple[Creature, ...]]
    ) -> dict[tuple[str, bool], int]:
        ids: dict[tuple[str, bool], int] = {}
        for team in teams.values():
            for creature in team:
                data = self._set_adapter.to_showdown_set(creature)
                identifier = showdown_sprite_identifier(
                    data.species,
                    creature.current_form.name if creature.current_form else None,
                )
                ids[(identifier, creature.is_shiny)] = creature.species.pokeapi_id
        return ids


class _RetrievedTaskSet(set):
    def __init__(self, player) -> None:
        super().__init__()
        self.player = player

    def add(self, task) -> None:
        super().add(task)
        task.add_done_callback(self._finish)

    def _finish(self, task) -> None:
        super().discard(task)
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            self.player._record_background_error(error)


def _consume_task_exception(task: asyncio.Task) -> None:
    if task.cancelled():
        return
    try:
        task.exception()
    except Exception:
        logger.debug("Unable to retrieve PvP task exception", exc_info=True)
