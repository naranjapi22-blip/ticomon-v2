from __future__ import annotations

import logging

from application.pvp.models import PvpPresentationStep

logger = logging.getLogger(__name__)


class PvpEventTranslator:
    """Translates Showdown protocol messages into compact board events."""

    def translate(self, messages: list[list[str]]) -> tuple[PvpPresentationStep, ...]:
        steps: list[PvpPresentationStep] = []
        for message in messages:
            if len(message) < 2:
                continue
            event = message[1]
            try:
                text = self._translate_event(event, message[2:])
            except Exception:
                logger.exception("Unable to translate PvP event=%s", event)
                text = None
            if text:
                steps.append(PvpPresentationStep(message=text))
        return tuple(steps)

    @staticmethod
    def _translate_event(event: str, values: list[str]) -> str | None:
        if event == "move" and len(values) >= 2:
            return f"{values[0]} used {values[1]}."
        if event == "-damage" and len(values) >= 2:
            return f"{values[0]} lost {values[1]} HP."
        if event == "-heal" and len(values) >= 2:
            return f"{values[0]} recovered HP."
        if event == "-status" and len(values) >= 2:
            return f"{values[0]} was afflicted with {values[1].upper()}."
        if event == "-curestatus" and len(values) >= 2:
            return f"{values[0]} was cured of {values[1].upper()}."
        if event == "-crit" and values:
            return f"A critical hit landed on {values[0]}."
        if event == "-supereffective" and values:
            return f"It was super effective against {values[0]}."
        if event == "-resisted" and values:
            return f"It was not very effective against {values[0]}."
        if event == "-immune" and values:
            return f"{values[0]} was immune."
        if event == "-fail" and values:
            return f"{values[0]}'s move failed."
        if event == "-miss" and values:
            return f"{values[0]}'s move missed."
        if event == "-protect" and values:
            return f"{values[0]} protected itself."
        if event == "-ability" and len(values) >= 2:
            return f"{values[0]}'s {values[1]} activated."
        if event == "switch" and len(values) >= 2:
            return f"{values[0]} sent out {values[1]}."
        if event == "faint" and values:
            return f"{values[0]} fainted."
        if event == "-weather" and values:
            return f"The weather changed to {values[0]}."
        if event == "-fieldstart" and values:
            return f"The field changed: {values[-1]}."
        if event == "win" and values:
            return f"{values[0]} won the battle."
        if event == "tie":
            return "The battle ended in a tie."
        return None
