from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable
from uuid import UUID

from application.pvp.models import (
    PvpAction,
    PvpEvent,
    PvpPresentationStep,
)
from application.pvp.snapshots import PvpBattleSnapshot, PvpPokemonSnapshot
from core.pvp.session import (
    ACTION_TIMEOUT_SECONDS,
    FORCED_SWITCH_TIMEOUT_SECONDS,
    PvpPhase,
)
from rendering.battle.pvp_sprite_urls import pvp_sprite_url

logger = logging.getLogger(__name__)

SendJson = Callable[[dict], Awaitable[None]]


@dataclass
class ActivityBattleRecord:
    session_id: UUID
    guild_id: int | None
    channel_id: int
    player_ids: tuple[int, int]
    display_names: dict[int, str]
    public_status: Callable[[str], Awaitable[None]] | None = None
    instance_id: str | None = None
    connections: dict[int, set[SendJson]] = field(
        default_factory=lambda: {1: set(), 2: set()}
    )
    latest_snapshots: dict[int, PvpBattleSnapshot] = field(default_factory=dict)
    sequence: int = 0
    finished: bool = False
    last_event: dict | None = None
    deadlines: dict[int, str] = field(default_factory=dict)
    cleanup_task: asyncio.Task | None = None

    def role_for(self, user_id: int) -> str:
        if user_id == self.player_ids[0]:
            return "player1"
        if user_id == self.player_ids[1]:
            return "player2"
        return "unauthorized"

    def connected_count(self) -> int:
        return sum(bool(connections) for connections in self.connections.values())


class PvptestActivityRegistry:
    """In-memory bridge between one experimental PvP session and Activity clients."""

    def __init__(self, pvp_service) -> None:
        self._pvp_service = pvp_service
        self._records: dict[UUID, ActivityBattleRecord] = {}
        self._channel_sessions: dict[int, UUID] = {}
        self._lock = asyncio.Lock()

    async def bind(
        self,
        *,
        session_id: UUID,
        guild_id: int | None,
        channel_id: int,
        player_ids: tuple[int, int],
        display_names: dict[int, str],
        public_status: Callable[[str], Awaitable[None]] | None = None,
    ) -> ActivityBattleRecord:
        async with self._lock:
            existing_id = self._channel_sessions.get(channel_id)
            if existing_id is not None and existing_id != session_id:
                raise ValueError(
                    "An Activity PvP test is already active in this channel."
                )
            record = ActivityBattleRecord(
                session_id=session_id,
                guild_id=guild_id,
                channel_id=channel_id,
                player_ids=player_ids,
                display_names=dict(display_names),
                public_status=public_status,
            )
            self._records[session_id] = record
            self._channel_sessions[channel_id] = session_id
            return record

    def get(self, session_id: UUID) -> ActivityBattleRecord:
        try:
            return self._records[session_id]
        except KeyError as error:
            raise ValueError("The Activity PvP test session was not found.") from error

    def find_for_channel(self, channel_id: int) -> ActivityBattleRecord | None:
        session_id = self._channel_sessions.get(channel_id)
        return self._records.get(session_id) if session_id is not None else None

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
        record.connections[1 if role == "player1" else 2].add(send_json)
        await send_json(self._state_message(record, role))
        await self._send_snapshot(record, user_id, send_json)
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
            await self._publish_status(record)

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
        await self._broadcast_snapshot(record, sequence=record.sequence)

    async def handle_actions(self, session_id: UUID, trainer_id: int, legal) -> None:
        record = self._records.get(session_id)
        if record is None:
            return
        timeout = (
            FORCED_SWITCH_TIMEOUT_SECONDS
            if legal.forced_switch
            else ACTION_TIMEOUT_SECONDS
        )
        deadline = datetime.now(timezone.utc).timestamp() + timeout
        record.deadlines[trainer_id] = datetime.fromtimestamp(
            deadline, timezone.utc
        ).isoformat()
        snapshot = record.latest_snapshots.get(trainer_id)
        if snapshot is not None:
            record.sequence += 1
            await self._broadcast_to(
                record.connections[1 if trainer_id == record.player_ids[0] else 2],
                self._snapshot_message(record, snapshot, record.sequence),
            )

    async def handle_finished(self, session_id: UUID, _battle: object) -> None:
        record = self._records.get(session_id)
        if record is None:
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
        await self._broadcast(record, payload)
        if record.public_status is not None:
            await record.public_status(
                "Battle finished. The final result is available in the Activity."
            )
        record.cleanup_task = asyncio.create_task(self._delayed_cleanup(session_id))

    async def cleanup(self, session_id: UUID) -> None:
        record = self._records.pop(session_id, None)
        if record is None:
            return
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
            return
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
            await self._broadcast_to(connections, payload)

    async def _broadcast(self, record: ActivityBattleRecord, payload: dict) -> None:
        for connections in record.connections.values():
            await self._broadcast_to(connections, payload)

    async def _broadcast_to(self, connections: set[SendJson], payload: dict) -> None:
        for send_json in tuple(connections):
            try:
                await send_json(payload)
            except Exception:
                connections.discard(send_json)
                logger.debug("Unable to send Activity update", exc_info=True)

    async def _publish_status(self, record: ActivityBattleRecord) -> None:
        if record.public_status is not None:
            await record.public_status(
                f"Activity status: {record.connected_count()}/2 connected"
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
        return {
            "type": "battle_snapshot",
            "sequence": sequence,
            "turn": snapshot.turn,
            "phase": session.phase.value,
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
    sprite_url = pokemon.capture_sprite_url
    if sprite_url is None and pokemon.sprite_identifier:
        sprite_url = pvp_sprite_url(
            pokemon.sprite_identifier,
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
        "source_side": source.actor,
        "target_side": source.target,
        "damage": source.damage,
        "healing": source.healing,
        "status": source.status,
        "switch": source.switch,
        "fainted": source.fainted,
    }
