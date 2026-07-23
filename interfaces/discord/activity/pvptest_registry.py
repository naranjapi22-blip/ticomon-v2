from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable
from uuid import UUID

from application.pvp.log_context import (
    format_pvp_context,
    safe_error_message,
    safe_traceback,
)
from application.pvp.models import (
    PvpAction,
    PvpEvent,
    PvpLegalActions,
    PvpPresentationStep,
)
from application.pvp.snapshots import PvpBattleSnapshot, PvpPokemonSnapshot
from core.pvp.session import (
    ACTION_TIMEOUT_SECONDS,
    FORCED_SWITCH_TIMEOUT_SECONDS,
    PvpPhase,
)
from interfaces.discord.activity.sprite_urls import activity_sprite_url

logger = logging.getLogger(__name__)

PROMPT_DELIVERY_TIMEOUT_SECONDS = 30

SendJson = Callable[[dict], Awaitable[None]]


@dataclass
class ActivityBattleRecord:
    session_id: UUID
    guild_id: int | None
    channel_id: int
    player_ids: tuple[int, int]
    display_names: dict[int, str]
    public_status: Callable[[str], Awaitable[None]] | None = None
    public_result: Callable[[str], Awaitable[None]] | None = None
    instance_id: str | None = None
    connections: dict[int, set[SendJson]] = field(
        default_factory=lambda: {1: set(), 2: set()}
    )
    latest_snapshots: dict[int, PvpBattleSnapshot] = field(default_factory=dict)
    sequence: int = 0
    finished: bool = False
    last_event: dict | None = None
    result_posted: bool = False
    deadlines: dict[int, str] = field(default_factory=dict)
    cleanup_task: asyncio.Task | None = None
    ready_event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    battle_started: bool = False
    prompt_ready_events: dict[str, asyncio.Event] = field(
        default_factory=dict, repr=False
    )
    prompt_connection_events: dict[int, asyncio.Event] = field(
        default_factory=lambda: {1: asyncio.Event(), 2: asyncio.Event()}, repr=False
    )
    prompt_published_at: dict[str, str] = field(default_factory=dict, repr=False)
    prompt_acknowledged_at: dict[str, str] = field(default_factory=dict, repr=False)

    def role_for(self, user_id: int) -> str:
        if user_id == self.player_ids[0]:
            return "player1"
        if user_id == self.player_ids[1]:
            return "player2"
        return "unauthorized"

    def connected_count(self) -> int:
        return sum(bool(connections) for connections in self.connections.values())

    def connected_for(self, trainer_id: int) -> bool:
        role = 1 if trainer_id == self.player_ids[0] else 2
        return bool(self.connections[role])


class PvptestActivityRegistry:
    """In-memory bridge between one experimental PvP session and Activity clients."""

    def __init__(self, pvp_service) -> None:
        self._pvp_service = pvp_service
        self._records: dict[UUID, ActivityBattleRecord] = {}
        self._channel_sessions: dict[int, UUID] = {}
        self._completed_records: dict[UUID, ActivityBattleRecord] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _context(record: ActivityBattleRecord) -> str:
        return format_pvp_context(
            {
                "session_id": str(record.session_id),
                "guild_id": record.guild_id if record.guild_id is not None else "-",
                "channel_id": record.channel_id,
                "player1_id": record.player_ids[0],
                "player2_id": record.player_ids[1],
            }
        )

    async def bind(
        self,
        *,
        session_id: UUID,
        guild_id: int | None,
        channel_id: int,
        player_ids: tuple[int, int],
        display_names: dict[int, str],
        public_status: Callable[[str], Awaitable[None]] | None = None,
        public_result: Callable[[str], Awaitable[None]] | None = None,
    ) -> ActivityBattleRecord:
        async with self._lock:
            existing_id = self._channel_sessions.get(channel_id)
            if existing_id is not None and existing_id != session_id:
                raise ValueError(
                    "An Activity PvP test is already active in this channel."
                )
            if existing_id == session_id:
                return self._records[session_id]
            record = ActivityBattleRecord(
                session_id=session_id,
                guild_id=guild_id,
                channel_id=channel_id,
                player_ids=player_ids,
                display_names=dict(display_names),
                public_status=public_status,
                public_result=public_result,
            )
            self._records[session_id] = record
            self._channel_sessions[channel_id] = session_id
            logger.info(
                "pvp_activity_session_bound %s battle_started=%s",
                self._context(record),
                record.battle_started,
            )
            return record

    def get(self, session_id: UUID) -> ActivityBattleRecord:
        try:
            return self._records[session_id]
        except KeyError as error:
            raise ValueError("The Activity PvP test session was not found.") from error

    def find_for_channel(self, channel_id: int) -> ActivityBattleRecord | None:
        session_id = self._channel_sessions.get(channel_id)
        return self._records.get(session_id) if session_id is not None else None

    def completed(self, session_id: UUID) -> ActivityBattleRecord:
        try:
            return self._completed_records[session_id]
        except KeyError as error:
            raise ValueError(
                "The completed Activity PvP test was not found."
            ) from error

    def action_handler(
        self, session_id: UUID
    ) -> Callable[[int, PvpLegalActions], Awaitable[bool]]:
        async def handle(trainer_id: int, legal: PvpLegalActions) -> bool:
            return await self.handle_actions(session_id, trainer_id, legal)

        return handle

    async def connect(
        self,
        *,
        session_id: UUID,
        user_id: int,
        guild_id: int | None,
        channel_id: int,
        instance_id: str,
        send_json: SendJson,
    ) -> str:
        record = self.get(session_id)
        if record.guild_id != guild_id or record.channel_id != channel_id:
            raise PermissionError("This Activity is not connected to the PvP channel.")
        if record.instance_id is None:
            record.instance_id = instance_id
        elif record.instance_id != instance_id:
            raise PermissionError("This Activity is not the matched Activity instance.")
        role = record.role_for(user_id)
        if role == "unauthorized":
            await send_json(self._state_message(record, role))
            return role
        connections = record.connections[1 if role == "player1" else 2]
        replaced = bool(connections)
        connections.clear()
        connections.add(send_json)
        logger.info(
            "pvp_activity_socket_connected %s user_id=%s role=%s replaced=%s "
            "sockets=%s/2 player1_socket_connected=%s player2_socket_connected=%s "
            "battle_started=%s",
            self._context(record),
            user_id,
            role,
            replaced,
            record.connected_count(),
            bool(record.connections[1]),
            bool(record.connections[2]),
            record.battle_started,
        )
        await send_json(self._state_message(record, role))
        await self._send_snapshot(record, user_id, send_json)
        record.prompt_connection_events[1 if role == "player1" else 2].set()
        if record.connected_count() == 2 and not record.battle_started:
            record.ready_event.set()
        elif record.connected_count() < 2 and not record.battle_started:
            record.ready_event.clear()
        await self._broadcast_state(record)
        await self._publish_status(record)
        return role

    async def disconnect(
        self, session_id: UUID, user_id: int, send_json: SendJson
    ) -> None:
        record = self._records.get(session_id)
        if record is None:
            return
        role = record.role_for(user_id)
        if role in {"player1", "player2"}:
            record.connections[1 if role == "player1" else 2].discard(send_json)
            role_number = 1 if role == "player1" else 2
            if not record.connections[role_number]:
                record.prompt_connection_events[role_number].clear()
            if record.connected_count() < 2 and not record.battle_started:
                record.ready_event.clear()
            logger.info(
                "pvp_activity_socket_disconnected %s user_id=%s role=%s "
                "sockets=%s/2 battle_started=%s",
                self._context(record),
                user_id,
                role,
                record.connected_count(),
                record.battle_started,
            )
            await self._broadcast_state(record)
            await self._publish_status(record)

    async def wait_until_ready(self, session_id: UUID) -> None:
        record = self.get(session_id)
        try:
            while record.connected_count() < 2:
                session = self._pvp_service.registry.get(session_id)
                logger.info(
                    "pvp_start_check %s teams=%s/%s sockets=%s/2 started=%s "
                    "should_start=false player1_team_ready=%s player2_team_ready=%s "
                    "player1_socket_connected=%s player2_socket_connected=%s "
                    "showdown_task_exists=%s",
                    self._context(record),
                    len(session.confirmed_teams),
                    len(session.player_ids),
                    record.connected_count(),
                    record.battle_started,
                    session.initiator_id in session.confirmed_teams,
                    session.opponent_id in session.confirmed_teams,
                    bool(record.connections[1]),
                    bool(record.connections[2]),
                    session.startup_task is not None,
                )
                await asyncio.wait_for(record.ready_event.wait(), timeout=180)
            if record.connected_count() < 2:
                raise asyncio.TimeoutError
            session = self._pvp_service.registry.get(session_id)
            logger.info(
                "pvp_start_check %s teams=%s/%s sockets=%s/2 started=%s "
                "should_start=true player1_team_ready=%s player2_team_ready=%s "
                "player1_socket_connected=%s player2_socket_connected=%s "
                "showdown_task_exists=%s",
                self._context(record),
                len(session.confirmed_teams),
                len(session.player_ids),
                record.connected_count(),
                record.battle_started,
                session.initiator_id in session.confirmed_teams,
                session.opponent_id in session.confirmed_teams,
                bool(record.connections[1]),
                bool(record.connections[2]),
                session.startup_task is not None,
            )
            record.battle_started = True
        except asyncio.TimeoutError as error:
            await self.cleanup(session_id)
            raise ValueError(
                "Both players must join the PvP Activity before the battle starts."
            ) from error

    async def handle_event(
        self, session_id: UUID, step: PvpPresentationStep | str
    ) -> None:
        record = self._records.get(session_id)
        if record is None:
            return
        record.sequence += 1
        payload = {
            "type": "battle_events",
            "sequence": record.sequence,
            "events": [event_to_dto(step)],
        }
        record.last_event = payload
        if isinstance(step, str) and "startup timed out" in step.casefold():
            payload = {
                "type": "startup_error",
                "message": "The battle did not start before the startup timeout.",
            }
        logger.info(
            "pvp_activity_publish %s type=%s sequence=%s index=0 clients=%s",
            self._context(record),
            payload["type"],
            record.sequence,
            record.connected_count(),
        )
        await self._broadcast(record, payload)
        if isinstance(step, str) and "could not start" in step.casefold():
            await self.cleanup(session_id)

    async def handle_snapshot(
        self, session_id: UUID, snapshot: PvpBattleSnapshot
    ) -> None:
        record = self._records.get(session_id)
        if record is None:
            return
        previous = record.latest_snapshots.get(snapshot.player_id)
        if previous is not None and snapshot.turn < previous.turn:
            return
        record.latest_snapshots[snapshot.player_id] = snapshot
        record.sequence += 1
        logger.info(
            "pvp_activity_publish %s type=battle_snapshot sequence=%s "
            "player_id=%s turn=%s clients=%s",
            self._context(record),
            record.sequence,
            snapshot.player_id,
            snapshot.turn,
            record.connected_count(),
        )
        await self._broadcast_snapshot(record, sequence=record.sequence)

    async def handle_actions(self, session_id: UUID, trainer_id: int, legal) -> bool:
        record = self._records.get(session_id)
        if record is None:
            return False
        request_id = self._action_request_id(session_id, trainer_id)
        prompt_event = asyncio.Event()
        record.prompt_ready_events[request_id] = prompt_event
        record.prompt_published_at[request_id] = datetime.now(timezone.utc).isoformat()
        snapshot = record.latest_snapshots.get(trainer_id)
        if snapshot is not None:
            record.sequence += 1
            role = 1 if trainer_id == record.player_ids[0] else 2
            logger.info(
                "pvp_activity_prompt_published %s request_id=%s trainer_id=%s "
                "forced_switch=%s actor_id=%s sequence=%s clients=%s "
                "legal_moves_count=%s legal_switches_count=%s",
                self._context(record),
                request_id,
                trainer_id,
                legal.forced_switch,
                trainer_id,
                record.sequence,
                len(record.connections[role]),
                len(legal.moves),
                len(legal.switches),
            )
            await self._broadcast_to(
                record.connections[role],
                self._snapshot_message(record, snapshot, record.sequence),
                context=self._context(record),
                record=record,
            )
        if legal.forced_switch:
            await self._broadcast_state(record)
        role = 1 if trainer_id == record.player_ids[0] else 2
        set_prompt_client_connected = getattr(
            self._pvp_service, "set_prompt_client_connected", None
        )
        if set_prompt_client_connected is not None:
            set_prompt_client_connected(
                session_id, trainer_id, bool(record.connections[role])
            )
        if not record.connections[role]:
            logger.warning(
                "pvp_activity_prompt_waiting_for_client %s request_id=%s "
                "trainer_id=%s forced_switch=%s",
                self._context(record),
                request_id,
                trainer_id,
                legal.forced_switch,
            )
        delivered = await self._wait_for_prompt_ready(
            record, trainer_id, request_id, prompt_event
        )
        record.prompt_ready_events.pop(request_id, None)
        if not delivered:
            logger.warning(
                "pvp_activity_prompt_delivery_timeout %s request_id=%s "
                "trainer_id=%s forced_switch=%s clients=%s",
                self._context(record),
                request_id,
                trainer_id,
                legal.forced_switch,
                record.connected_count(),
            )
            return False
        timeout = (
            FORCED_SWITCH_TIMEOUT_SECONDS
            if legal.forced_switch
            else ACTION_TIMEOUT_SECONDS
        )
        deadline = datetime.now(timezone.utc).timestamp() + timeout
        record.deadlines[trainer_id] = datetime.fromtimestamp(
            deadline, timezone.utc
        ).isoformat()
        logger.info(
            "pvp_activity_prompt_acknowledged %s request_id=%s trainer_id=%s "
            "forced_switch=%s timeout_started=true",
            self._context(record),
            request_id,
            trainer_id,
            legal.forced_switch,
        )
        return True

    async def _wait_for_prompt_ready(
        self,
        record: ActivityBattleRecord,
        trainer_id: int,
        request_id: str,
        prompt_event: asyncio.Event,
    ) -> bool:
        role = 1 if trainer_id == record.player_ids[0] else 2
        deadline = asyncio.get_running_loop().time() + PROMPT_DELIVERY_TIMEOUT_SECONDS
        while True:
            if prompt_event.is_set():
                return True
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                return False
            if not record.connections[role]:
                try:
                    await asyncio.wait_for(
                        record.prompt_connection_events[role].wait(), remaining
                    )
                except asyncio.TimeoutError:
                    return False
                continue
            try:
                await asyncio.wait_for(prompt_event.wait(), remaining)
            except asyncio.TimeoutError:
                return False

    async def prompt_ready(
        self, session_id: UUID, trainer_id: int, request_id: str
    ) -> bool:
        record = self._records.get(session_id)
        if record is None or record.role_for(trainer_id) == "unauthorized":
            return False
        event = record.prompt_ready_events.get(request_id)
        if event is None:
            return False
        current_request = self._action_request_id(session_id, trainer_id)
        if current_request != request_id or not record.connected_for(trainer_id):
            return False
        record.prompt_acknowledged_at[request_id] = datetime.now(
            timezone.utc
        ).isoformat()
        event.set()
        logger.info(
            "pvp_activity_prompt_ack %s request_id=%s trainer_id=%s "
            "forced_switch=%s",
            self._context(record),
            request_id,
            trainer_id,
            self._pvp_service.legal_actions_for(session_id, trainer_id).forced_switch,
        )
        return True

    def _action_request_id(self, session_id: UUID, trainer_id: int) -> str:
        request_id = getattr(self._pvp_service, "action_request_id", None)
        if request_id is not None:
            return request_id(session_id, trainer_id)
        return self._pvp_service.registry.get(session_id).active_action_requests[
            trainer_id
        ]

    async def handle_finished(self, session_id: UUID, _battle: object) -> None:
        record = self._records.get(session_id)
        if record is None or record.finished:
            return
        record.finished = True
        session = self._pvp_service.registry.get(session_id)
        payload = {
            "type": "battle_finished",
            "sequence": record.sequence + 1,
            "winner": (
                {
                    "user_id": session.final_winner_id,
                    "display_name": record.display_names.get(session.final_winner_id),
                }
                if session.final_winner_id is not None
                else None
            ),
            "reason": session.final_reason
            or ("tie" if session.final_tie else "normal"),
        }
        record.sequence += 1
        logger.info(
            "pvp_activity_publish %s type=battle_finished sequence=%s clients=%s",
            self._context(record),
            record.sequence,
            record.connected_count(),
        )
        await self._broadcast(record, payload)
        await self._post_result(record, session)
        if record.public_status is not None:
            try:
                await record.public_status(
                    "Battle finished. The final result is available in the Activity."
                )
            except Exception:
                logger.debug(
                    "Unable to publish completed Activity status session_id=%s",
                    session_id,
                    exc_info=True,
                )
        await self.cleanup(session_id)

    async def _post_result(self, record: ActivityBattleRecord, session) -> None:
        if record.public_result is None or record.result_posted:
            return
        winner_id = session.final_winner_id
        if session.final_tie or winner_id is None:
            result = "The PvP battle ended in a tie."
        else:
            loser_id = next(
                player_id for player_id in record.player_ids if player_id != winner_id
            )
            winner = record.display_names.get(winner_id, "The winner")
            loser = record.display_names.get(loser_id, "the opponent")
            result = f"{winner} defeated {loser}!"
        record.result_posted = True
        try:
            await record.public_result(result)
        except Exception:
            logger.warning(
                "Unable to post Activity PvP result session_id=%s",
                record.session_id,
                exc_info=True,
            )

    async def cleanup(self, session_id: UUID) -> None:
        record = self._records.pop(session_id, None)
        if record is None:
            return
        if record.finished:
            self._completed_records[session_id] = record
        if (
            record.cleanup_task is not asyncio.current_task()
            and record.cleanup_task is not None
        ):
            record.cleanup_task.cancel()
        if self._channel_sessions.get(record.channel_id) == session_id:
            self._channel_sessions.pop(record.channel_id, None)
        for connections in record.connections.values():
            for send_json in tuple(connections):
                try:
                    await send_json({"type": "session_closed", "reason": "cleanup"})
                except Exception:
                    logger.debug(
                        "Unable to notify Activity client during cleanup", exc_info=True
                    )

    async def handle_pvp_cleanup(self, session_id: UUID) -> None:
        record = self._records.get(session_id)
        if record is not None and not record.finished:
            await self.cleanup(session_id)

    async def _delayed_cleanup(self, session_id: UUID) -> None:
        try:
            await asyncio.sleep(60)
            await self.cleanup(session_id)
        except asyncio.CancelledError:
            return

    async def _send_snapshot(
        self, record: ActivityBattleRecord, user_id: int, send_json: SendJson
    ) -> None:
        snapshot = record.latest_snapshots.get(user_id)
        if snapshot is None:
            logger.info(
                "pvp_activity_snapshot_unavailable %s user_id=%s",
                self._context(record),
                user_id,
            )
            return
        logger.info(
            "pvp_activity_snapshot_delivery %s sequence=%s player_id=%s "
            "recipients=1 legal_actions=initial",
            self._context(record),
            record.sequence,
            user_id,
        )
        await send_json(self._snapshot_message(record, snapshot, record.sequence))

    async def _broadcast_snapshot(
        self, record: ActivityBattleRecord, *, sequence: int
    ) -> None:
        for user_id, connections in (
            (record.player_ids[0], record.connections[1]),
            (record.player_ids[1], record.connections[2]),
        ):
            snapshot = record.latest_snapshots.get(user_id)
            if snapshot is None:
                continue
            payload = self._snapshot_message(record, snapshot, sequence)
            logger.info(
                "pvp_activity_snapshot_delivery %s sequence=%s player_id=%s "
                "recipients=%s legal_actions=%s",
                self._context(record),
                sequence,
                user_id,
                len(connections),
                {
                    "moves": len(payload["legal_actions"]["moves"]),
                    "switches": len(payload["legal_actions"]["switches"]),
                    "forced_switch": payload["legal_actions"]["forced_switch"],
                },
            )
            await self._broadcast_to(
                connections, payload, context=self._context(record), record=record
            )

    async def _broadcast(self, record: ActivityBattleRecord, payload: dict) -> None:
        for connections in record.connections.values():
            await self._broadcast_to(
                connections, payload, context=self._context(record), record=record
            )

    async def _broadcast_to(
        self,
        connections: set[SendJson],
        payload: dict,
        *,
        context="session_id=-",
        record: ActivityBattleRecord | None = None,
    ) -> None:
        if not connections:
            log = (
                logger.warning
                if record is not None and record.battle_started
                else logger.info
            )
            log(
                "pvp_activity_publish_no_clients %s type=%s sequence=%s "
                "phase=%s battle_started=%s request_id=%s",
                context,
                payload.get("type"),
                payload.get("sequence"),
                self._record_phase(record),
                record.battle_started if record is not None else False,
                payload.get("request_id"),
            )
        for send_json in tuple(connections):
            try:
                await send_json(payload)
            except Exception as error:
                connections.discard(send_json)
                logger.error(
                    "pvp_activity_send_failed %s type=%s sequence=%s "
                    "error_type=%s error=%s stack_trace=%s",
                    context,
                    payload.get("type"),
                    payload.get("sequence"),
                    type(error).__name__,
                    safe_error_message(error),
                    safe_traceback(error),
                )

    def _record_phase(self, record: ActivityBattleRecord | None) -> str:
        if record is None:
            return "unknown"
        try:
            return self._pvp_service.registry.get(record.session_id).phase.value
        except ValueError:
            return "unknown"

    async def _publish_status(self, record: ActivityBattleRecord) -> None:
        if record.public_status is not None:
            logger.info(
                "pvp_activity_presence_published %s sockets=%s/2",
                self._context(record),
                record.connected_count(),
            )
            await record.public_status(
                f"Activity status: {record.connected_count()}/2 connected"
            )

    async def _broadcast_state(self, record: ActivityBattleRecord) -> None:
        logger.info(
            "pvp_activity_publish %s type=session_state clients=%s",
            self._context(record),
            record.connected_count(),
        )
        for role, connections in record.connections.items():
            await self._broadcast_to(
                connections,
                self._state_message(
                    record,
                    "player1" if role == 1 else "player2",
                ),
                context=self._context(record),
                record=record,
            )

    def _state_message(self, record: ActivityBattleRecord, role: str) -> dict:
        try:
            phase = self._pvp_service.registry.get(record.session_id).phase.value
        except ValueError:
            phase = PvpPhase.CANCELLED.value
        return {
            "type": "session_state",
            "session_id": str(record.session_id),
            "role": role,
            "phase": phase,
            "players_connected": record.connected_count(),
            "players_expected": 2,
            "battle_started": record.battle_started,
            "required_user_id": self._required_action_user_id(record),
            "waiting_for_reconnect": self._waiting_for_reconnect(record),
            "players": [
                {
                    "role": "player1",
                    "user_id": record.player_ids[0],
                    "name": record.display_names.get(record.player_ids[0], "Player 1"),
                },
                {
                    "role": "player2",
                    "user_id": record.player_ids[1],
                    "name": record.display_names.get(record.player_ids[1], "Player 2"),
                },
            ],
        }

    def _required_action_user_id(self, record: ActivityBattleRecord) -> int | None:
        try:
            session = self._pvp_service.registry.get(record.session_id)
        except ValueError:
            return None
        if session.phase is not PvpPhase.FORCED_SWITCH:
            return None
        return next(iter(session.active_action_requests), None)

    def _waiting_for_reconnect(self, record: ActivityBattleRecord) -> bool:
        user_id = self._required_action_user_id(record)
        if user_id is None:
            return False
        role = record.role_for(user_id)
        return not record.connections[1 if role == "player1" else 2]

    def _snapshot_message(
        self, record: ActivityBattleRecord, snapshot: PvpBattleSnapshot, sequence: int
    ) -> dict:
        legal_actions = {"moves": [], "switches": [], "forced_switch": False}
        try:
            legal = self._pvp_service.legal_actions_for(
                record.session_id, snapshot.player_id
            )
            legal_actions = legal_actions_to_dto(legal)
        except ValueError:
            pass
        session = self._pvp_service.registry.get(record.session_id)
        request_id = session.active_action_requests.get(snapshot.player_id)
        return {
            "type": "battle_snapshot",
            "sequence": sequence,
            "turn": snapshot.turn,
            "phase": session.phase.value,
            "request_id": request_id,
            "deadline": record.deadlines.get(snapshot.player_id),
            "self": pokemon_to_dto(snapshot.player_active, player_side=True),
            "opponent": pokemon_to_dto(snapshot.opponent_active, player_side=False),
            "self_team": [
                pokemon_to_dto(pokemon, player_side=True)
                for pokemon in snapshot.player_team
            ],
            "opponent_team": [
                pokemon_to_dto(pokemon, player_side=False)
                for pokemon in snapshot.opponent_team
            ],
            "self_remaining": snapshot.player_remaining,
            "opponent_remaining": snapshot.opponent_remaining,
            "legal_actions": legal_actions,
            "message": (
                event_to_dto(snapshot.last_decisive_event)
                if snapshot.last_decisive_event
                else None
            ),
        }


def legal_actions_to_dto(legal) -> dict:
    return {
        "forced_switch": legal.forced_switch,
        "moves": [
            action_to_dto(action, index + 1) for index, action in enumerate(legal.moves)
        ],
        "switches": [
            action_to_dto(action, index + 1)
            for index, action in enumerate(legal.switches)
        ],
    }


def action_to_dto(action: PvpAction, slot: int) -> dict:
    return {
        "slot": slot,
        "kind": action.kind.value,
        "name": action.label,
        "detail": action.detail,
        "type": action.move_type,
        "category": action.category,
        "pp": action.detail,
        "hp_current": action.hp_current,
        "hp_max": action.hp_max,
        "fainted": action.fainted,
    }


def pokemon_to_dto(
    pokemon: PvpPokemonSnapshot | None, *, player_side: bool
) -> dict | None:
    if pokemon is None:
        return None
    sprite_url = None
    if pokemon.pokeapi_id is not None:
        sprite_url = activity_sprite_url(
            pokemon.pokeapi_id,
            player_side=player_side,
            shiny=pokemon.shiny,
        )
    return {
        "name": pokemon.species_name,
        "form": pokemon.form_name,
        "hp_current": pokemon.current_hp,
        "hp_max": pokemon.max_hp,
        "hp_fraction": pokemon.hp_fraction,
        "status": pokemon.status,
        "fainted": pokemon.fainted,
        "sprite_url": sprite_url,
        "shiny": pokemon.shiny,
    }


def event_to_dto(event: PvpPresentationStep | PvpEvent | str | None) -> dict:
    if isinstance(event, PvpPresentationStep):
        source = event.event
        message = event.message
        turn = event.turn
    else:
        source = event if isinstance(event, PvpEvent) else None
        message = str(event) if isinstance(event, str) else ""
        turn = None
    if source is None:
        return {"kind": "message", "message": message, "turn": turn}
    kind = "message"
    if source.move_name:
        kind = "move"
    elif source.switch:
        kind = "switch"
    elif source.fainted:
        kind = "faint"
    elif source.healing is not None:
        kind = "healing"
    elif source.damage is not None or source.direct_damage is not None:
        kind = "damage"
    elif source.status:
        kind = "status_applied"
    return {
        "kind": kind,
        "message": message,
        "turn": turn,
        "move_name": source.move_name,
        # Legacy events had no category; keep their historical physical
        # presentation explicitly instead of inferring from move data.
        "category": source.category or "physical",
        "source_side": source.actor,
        "target_side": source.target,
        "damage": source.damage,
        "healing": source.healing,
        "status": source.status,
        "switch": source.switch,
        "fainted": source.fainted,
    }
