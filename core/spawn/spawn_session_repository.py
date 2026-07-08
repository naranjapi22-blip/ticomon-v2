from abc import ABC, abstractmethod

from core.spawn.session import SpawnSession


class SpawnSessionRepository(ABC):
    """
    Stores active spawn sessions by guild.
    """

    @abstractmethod
    async def save(
        self,
        guild_id: int,
        session: SpawnSession,
    ) -> None:
        """
        Stores the active spawn session for a guild.
        """

    @abstractmethod
    async def get_active(
        self,
        guild_id: int,
    ) -> SpawnSession | None:
        """
        Returns the active spawn session for a guild.
        """

    @abstractmethod
    async def clear(
        self,
        guild_id: int,
    ) -> None:
        """
        Removes the active spawn session for a guild.
        """
