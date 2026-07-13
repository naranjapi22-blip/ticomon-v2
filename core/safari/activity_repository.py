import asyncio
from abc import ABC, abstractmethod

from core.safari.registration import SafariRegistration
from core.safari.session import SafariSession

SafariActivity = SafariRegistration | SafariSession


class SafariActivityRepository(ABC):
    @abstractmethod
    async def get_activity(self, guild_id: int) -> SafariActivity | None:
        pass

    @abstractmethod
    async def get_registration(
        self,
        guild_id: int,
    ) -> SafariRegistration | None:
        pass

    @abstractmethod
    async def save_registration(
        self,
        registration: SafariRegistration,
    ) -> None:
        pass

    @abstractmethod
    async def clear_registration(
        self,
        guild_id: int,
    ) -> None:
        pass

    @abstractmethod
    async def get_session(self, guild_id: int) -> SafariSession | None:
        pass

    @abstractmethod
    async def save_session(self, session: SafariSession) -> None:
        """Atomically replaces any registration for the session guild."""

    @abstractmethod
    async def clear_session(self, guild_id: int) -> None:
        pass

    @abstractmethod
    def lock(
        self,
        guild_id: int,
    ) -> asyncio.Lock:
        pass
