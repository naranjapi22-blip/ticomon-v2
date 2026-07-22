from __future__ import annotations

import asyncio
import json
import logging
import os

from aiohttp import WSMsgType, web

from interfaces.discord.activity.auth import ActivityAuthenticator
from interfaces.discord.activity.pvptest_registry import PvptestActivityRegistry

logger = logging.getLogger(__name__)


class PvptestActivityServer:
    """Optional aiohttp API for the experimental TicoMon Activity."""

    def __init__(self, registry: PvptestActivityRegistry) -> None:
        self.registry = registry
        self.authenticator = ActivityAuthenticator()
        self.app = web.Application(middlewares=[self._cors_middleware])
        self.app.add_routes(
            [
                web.get("/health", self.health),
                web.get("/api/activity/auth/challenge", self.auth_challenge),
                web.post("/api/activity/auth", self.auth),
                web.get("/api/activity/pvptest/session", self.session),
                web.get("/api/activity/pvptest/ws", self.websocket),
            ]
        )
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None

    async def start(self) -> None:
        host = "0.0.0.0"
        port = int(os.getenv("PORT") or os.getenv("ACTIVITY_API_PORT") or "8080")
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, host, port)
        await self.site.start()
        logger.info("Experimental Activity API listening on %s:%s", host, port)

    async def stop(self) -> None:
        if self.runner is not None:
            await self.runner.cleanup()
            self.runner = None
            self.site = None

    @web.middleware
    async def _cors_middleware(self, request: web.Request, handler):
        allowed = self._allowed_origins()
        origin = request.headers.get("Origin")
        if origin and origin not in allowed:
            return web.json_response({"error": "Origin is not allowed."}, status=403)
        if request.method == "OPTIONS":
            response = web.Response(status=204)
        else:
            response = await handler(request)
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization"
            )
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    @staticmethod
    def _allowed_origins() -> set[str]:
        configured = {
            value.strip()
            for value in os.getenv("ACTIVITY_ALLOWED_ORIGINS", "").split(",")
            if value.strip()
        }
        if configured:
            return configured
        return {"http://localhost:5173", "http://127.0.0.1:5173"}

    async def health(self, _request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "service": "ticomon-activity"})

    async def auth_challenge(self, _request: web.Request) -> web.Response:
        return web.json_response({"state": self.authenticator.create_state()})

    async def auth(self, request: web.Request) -> web.Response:
        try:
            body = await request.json()
            identity = await self.authenticator.exchange_code(
                code=str(body["code"]), state=str(body["state"])
            )
        except (KeyError, TypeError, ValueError, RuntimeError) as error:
            return web.json_response({"error": str(error)}, status=400)
        return web.json_response(
            {
                "session_token": identity.token,
                "user": {"id": str(identity.user_id), "name": identity.username},
                "expires_at": identity.expires_at,
            }
        )

    async def session(self, request: web.Request) -> web.Response:
        identity = self._identity_from_request(request)
        if identity is None:
            return web.json_response(
                {"error": "Activity authentication required."}, status=401
            )
        channel_id = self._int_query(request, "channel_id")
        record = self.registry.find_for_channel(channel_id) if channel_id else None
        if record is None:
            return web.json_response({"type": "no_active_session"})
        return web.json_response(
            {
                "type": "session_state",
                "session_id": str(record.session_id),
                "role": record.role_for(identity.user_id),
                "phase": self.registry._state_message(
                    record, record.role_for(identity.user_id)
                )["phase"],
                "players_connected": record.connected_count(),
                "players_expected": 2,
            }
        )

    async def websocket(self, request: web.Request) -> web.WebSocketResponse:
        origin = request.headers.get("Origin")
        if origin and origin not in self._allowed_origins():
            return web.Response(status=403, text="Origin is not allowed.")
        websocket = web.WebSocketResponse(heartbeat=30)
        await websocket.prepare(request)
        send_json = self._sender(websocket)
        session_id = None
        user_id = None
        try:
            message = await websocket.receive_json(timeout=10)
            if message.get("type") != "authenticate":
                await send_json(
                    {"type": "error", "message": "Authentication is required first."}
                )
                return websocket
            identity = self.authenticator.get_identity(
                str(message.get("session_token", ""))
            )
            if identity is None:
                await send_json(
                    {"type": "error", "message": "Activity authentication expired."}
                )
                return websocket
            record = self.registry.find_for_channel(int(message["channel_id"]))
            if record is None:
                await send_json({"type": "no_active_session"})
                return websocket
            session_id = record.session_id
            user_id = identity.user_id
            role = await self.registry.connect(
                session_id=session_id,
                user_id=identity.user_id,
                guild_id=self._optional_int(message.get("guild_id")),
                channel_id=int(message["channel_id"]),
                instance_id=str(message["instance_id"]),
                send_json=send_json,
            )
            await send_json({"type": "connection_ready", "role": role})
            async for incoming in websocket:
                if incoming.type is WSMsgType.TEXT:
                    await self._handle_message(
                        record, identity.user_id, json.loads(incoming.data), send_json
                    )
                elif incoming.type in {WSMsgType.CLOSE, WSMsgType.ERROR}:
                    break
        except (
            asyncio.TimeoutError,
            KeyError,
            TypeError,
            ValueError,
            PermissionError,
        ) as error:
            await send_json({"type": "error", "message": str(error)})
        finally:
            if session_id is not None and user_id is not None:
                await self.registry.disconnect(session_id, user_id, send_json)
        return websocket

    async def _handle_message(
        self, record, user_id: int, message: dict, send_json
    ) -> None:
        if record.role_for(user_id) == "unauthorized":
            await send_json(
                {
                    "type": "action_rejected",
                    "reason": "You are not a player in this test battle.",
                }
            )
            return
        if message.get("type") == "forfeit":
            await self.registry._pvp_service.forfeit(record.session_id, user_id)
            return
        if message.get("type") not in {"choose_move", "choose_switch"}:
            await send_json({"type": "error", "message": "Unknown Activity action."})
            return
        legal = self.registry._pvp_service.legal_actions_for(record.session_id, user_id)
        actions = legal.switches if message["type"] == "choose_switch" else legal.moves
        slot = int(message.get("slot", 0))
        if slot < 1 or slot > len(actions):
            await send_json(
                {"type": "action_rejected", "reason": "That action slot is not legal."}
            )
            return
        action = actions[slot - 1]
        accepted = await self.registry._pvp_service.submit_action(
            record.session_id, user_id, action
        )
        if not accepted:
            await send_json(
                {
                    "type": "action_rejected",
                    "reason": "The action was already submitted or expired.",
                }
            )

    @staticmethod
    def _sender(websocket: web.WebSocketResponse):
        async def send_json(payload: dict) -> None:
            if not websocket.closed:
                await websocket.send_json(payload)

        return send_json

    def _identity_from_request(self, request: web.Request):
        header = request.headers.get("Authorization", "")
        return self.authenticator.get_identity(header.removeprefix("Bearer ").strip())

    @staticmethod
    def _int_query(request: web.Request, name: str) -> int | None:
        value = request.query.get(name)
        return int(value) if value is not None else None

    @staticmethod
    def _optional_int(value) -> int | None:
        return int(value) if value is not None else None
