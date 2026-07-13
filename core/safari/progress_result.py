from __future__ import annotations

from dataclasses import dataclass

from core.safari.unlock import SafariUnlock


@dataclass(frozen=True, slots=True)
class SafariWorldProgressResult:
    created_unlocks: tuple[SafariUnlock, ...]
    current_progress: int
    daily_unlock_count: int
