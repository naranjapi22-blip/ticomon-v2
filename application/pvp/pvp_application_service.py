from __future__ import annotations

from core.pvp.session import PvpSessionRegistry


class PvpApplicationService:
    """Owns fast-PvP lifecycle state independently from the legacy battle flow."""

    def __init__(self, registry: PvpSessionRegistry | None = None) -> None:
        self.registry = registry or PvpSessionRegistry()

    def challenge(self, initiator_id: int, opponent_id: int):
        return self.registry.create(initiator_id, opponent_id)

    def decline(self, session_id):
        session = self.registry.get(session_id)
        session.cancel()
        self.registry.remove(session_id)

    def cleanup(self, session_id) -> None:
        self.registry.remove(session_id)
