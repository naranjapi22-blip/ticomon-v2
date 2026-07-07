from abc import ABC, abstractmethod

from core.spawn.session import SpawnSession


class SpawnSessionRepository(ABC):
    """
    Stores active spawn sessions.
    """

    @abstractmethod
    async def save(
        self,
        session: SpawnSession,
    ) -> None:
        """
        Stores an active spawn session.
        """

    @abstractmethod
    async def get_active(
        self,
    ) -> SpawnSession | None:
        """
        Returns the active spawn session.
        """
