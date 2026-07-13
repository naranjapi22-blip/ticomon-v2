import asyncio
from abc import ABC, abstractmethod

from core.safari.registration import SafariRegistration


class SafariActivityRepository(ABC):
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
    def lock(
        self,
        guild_id: int,
    ) -> asyncio.Lock:
        pass
