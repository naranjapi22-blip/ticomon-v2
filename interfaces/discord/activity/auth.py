from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass

import aiohttp


@dataclass(frozen=True)
class ActivityIdentity:
    token: str
    user_id: int
    username: str
    expires_at: float


class ActivityAuthenticator:
    """Exchanges Embedded App SDK OAuth codes and stores short-lived identities."""

    def __init__(self, *, ttl_seconds: int = 900) -> None:
        self._ttl_seconds = ttl_seconds
        self._pending_states: dict[str, float] = {}
        self._identities: dict[str, ActivityIdentity] = {}

    def _session_secret(self) -> str:
        secret = os.getenv("ACTIVITY_SESSION_SECRET")
        if not secret:
            raise RuntimeError(
                "ACTIVITY_SESSION_SECRET is required for Activity authentication."
            )
        return secret

    def _signed_token(self) -> str:
        token_id = secrets.token_urlsafe(32)
        signature = hmac.new(
            self._session_secret().encode("utf-8"),
            token_id.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"{token_id}.{signature}"

    def _is_valid_token(self, token: str) -> bool:
        try:
            token_id, signature = token.rsplit(".", 1)
        except ValueError:
            return False
        expected = hmac.new(
            self._session_secret().encode("utf-8"),
            token_id.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    def create_state(self) -> str:
        state = secrets.token_urlsafe(32)
        self._pending_states[state] = time.time() + 300
        return state

    def get_identity(self, token: str) -> ActivityIdentity | None:
        try:
            if not self._is_valid_token(token):
                return None
        except RuntimeError:
            return None
        identity = self._identities.get(token)
        if identity is None or identity.expires_at <= time.time():
            self._identities.pop(token, None)
            return None
        return identity

    async def exchange_code(self, *, code: str, state: str) -> ActivityIdentity:
        state_expiry = self._pending_states.pop(state, None)
        if state_expiry is None or state_expiry <= time.time():
            raise ValueError("The Activity authorization state is invalid or expired.")
        client_id = os.getenv("DISCORD_CLIENT_ID")
        client_secret = os.getenv("DISCORD_CLIENT_SECRET")
        self._session_secret()
        if not client_id or not client_secret:
            raise RuntimeError(
                "DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET are required "
                "for Activity authentication."
            )
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "code": code,
        }
        async with aiohttp.ClientSession() as http:
            async with http.post(
                "https://discord.com/api/oauth2/token", data=payload
            ) as response:
                if response.status >= 400:
                    raise ValueError("Discord authorization code exchange failed.")
                token_data = await response.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise ValueError("Discord did not return an access token.")
            async with http.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {access_token}"},
            ) as response:
                if response.status >= 400:
                    raise ValueError("Discord identity verification failed.")
                user_data = await response.json()
        try:
            user_id = int(user_data["id"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Discord returned an invalid user identity.") from error
        identity = ActivityIdentity(
            token=self._signed_token(),
            user_id=user_id,
            username=user_data.get("global_name")
            or user_data.get("username")
            or "Discord user",
            expires_at=time.time() + self._ttl_seconds,
        )
        self._identities[identity.token] = identity
        return identity
