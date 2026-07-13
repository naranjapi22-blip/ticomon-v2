import asyncio

from core.safari.activity_repository import SafariActivityRepository
from core.safari.registration import SafariRegistration
from core.safari.session import SafariSession


class InMemorySafariActivityRepository(SafariActivityRepository):
    def __init__(self) -> None:
        self._registrations: dict[int, SafariRegistration] = {}
        self._sessions: dict[int, SafariSession] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    async def get_activity(
        self,
        guild_id: int,
    ) -> SafariRegistration | SafariSession | None:
        return self._registrations.get(guild_id) or self._sessions.get(guild_id)

    async def get_registration(
        self,
        guild_id: int,
    ) -> SafariRegistration | None:
        return self._registrations.get(guild_id)

    async def save_registration(
        self,
        registration: SafariRegistration,
    ) -> None:
        if registration.guild_id in self._sessions:
            raise ValueError("Safari activity already exists for guild.")
        self._registrations[registration.guild_id] = registration

    async def clear_registration(
        self,
        guild_id: int,
    ) -> None:
        self._registrations.pop(guild_id, None)

    async def get_session(
        self,
        guild_id: int,
    ) -> SafariSession | None:
        return self._sessions.get(guild_id)

    async def save_session(
        self,
        session: SafariSession,
    ) -> None:
        self._registrations.pop(session.guild_id, None)
        self._sessions[session.guild_id] = session

    async def clear_session(
        self,
        guild_id: int,
    ) -> None:
        self._sessions.pop(guild_id, None)

    def lock(
        self,
        guild_id: int,
    ) -> asyncio.Lock:
        return self._locks.setdefault(guild_id, asyncio.Lock())
