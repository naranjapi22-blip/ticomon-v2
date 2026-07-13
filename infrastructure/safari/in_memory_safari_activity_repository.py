import asyncio

from core.safari.activity_repository import SafariActivityRepository
from core.safari.registration import SafariRegistration


class InMemorySafariActivityRepository(SafariActivityRepository):
    def __init__(self) -> None:
        self._registrations: dict[int, SafariRegistration] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    async def get_registration(
        self,
        guild_id: int,
    ) -> SafariRegistration | None:
        return self._registrations.get(guild_id)

    async def save_registration(
        self,
        registration: SafariRegistration,
    ) -> None:
        self._registrations[registration.guild_id] = registration

    async def clear_registration(
        self,
        guild_id: int,
    ) -> None:
        self._registrations.pop(guild_id, None)

    def lock(
        self,
        guild_id: int,
    ) -> asyncio.Lock:
        return self._locks.setdefault(guild_id, asyncio.Lock())
