from __future__ import annotations

import logging
import re
from dataclasses import replace

from application.pvp.models import PvpEvent, PvpPresentationStep
from application.pvp.snapshots import PvpBattleSnapshot

logger = logging.getLogger(__name__)


class PvpEventTranslator:
    """Translates Showdown protocol messages into readable turn summaries."""

    def __init__(self) -> None:
        self._last_hp: dict[str, tuple[int, int]] = {}

    def observe_snapshot(self, snapshot: PvpBattleSnapshot) -> None:
        for prefix, pokemon in (
            ("p1a", snapshot.player_active),
            ("p2a", snapshot.opponent_active),
        ):
            if pokemon is not None and pokemon.current_hp is not None:
                self._last_hp[_protocol_id(f"{prefix}: {pokemon.species_name}")] = (
                    pokemon.current_hp,
                    pokemon.max_hp or 0,
                )

    def translate(self, messages: list[list[str]]) -> tuple[PvpPresentationStep, ...]:
        steps: list[PvpPresentationStep] = []
        summary: list[str] = []
        structured: PvpEvent | None = None
        for message in messages:
            if len(message) < 2:
                continue
            event = message[1]
            values = message[2:]
            try:
                if event == "move" and len(values) >= 2:
                    if summary:
                        steps.append(self._step(summary, structured))
                    summary = [f"{_pokemon_name(values[0])} used {values[1]}."]
                    structured = PvpEvent(
                        actor=_pokemon_name(values[0]),
                        move_name=_safe_protocol_text(values[1]),
                        target=(_pokemon_name(values[2]) if len(values) >= 3 else None),
                    )
                    continue

                if event == "-damage" and len(values) >= 2:
                    previous = self._last_hp.get(_protocol_id(values[0]))
                    current, _ = _parse_hp(values[1])
                    text = self._damage_text(values[0], values[1])
                    if structured is not None:
                        structured = replace(
                            structured,
                            target=_pokemon_name(values[0]),
                            damage=(
                                previous[0] - current
                                if previous is not None and previous[0] >= current
                                else None
                            ),
                        )
                elif event == "-heal" and len(values) >= 2:
                    previous = self._last_hp.get(_protocol_id(values[0]))
                    current, maximum = _parse_hp(values[1])
                    self._last_hp[_protocol_id(values[0])] = (current, maximum)
                    if structured is not None:
                        structured = replace(
                            structured,
                            target=_pokemon_name(values[0]),
                            healing=(
                                current - previous[0]
                                if previous is not None and current >= previous[0]
                                else None
                            ),
                        )
                    text = self._translate_event(event, values)
                else:
                    text = self._translate_event(event, values)
                if structured is None:
                    if event in {"-damage", "-heal"} and values:
                        structured = PvpEvent(target=_pokemon_name(values[0]))
                    elif event == "switch" and len(values) >= 2:
                        structured = PvpEvent(
                            actor=_pokemon_name(values[0]),
                            switch=_safe_protocol_text(values[1]),
                        )
                if text:
                    summary.append(text)
                structured = self._update_structured(structured, event, values)
                if event in {"win", "tie"} and summary:
                    steps.append(self._step(summary, structured))
                    summary = []
                    structured = None
            except Exception:
                logger.exception("Unable to translate PvP event=%s", event)

        if summary:
            steps.append(self._step(summary, structured))
        return tuple(steps)

    def _step(
        self,
        summary: list[str],
        structured: PvpEvent | None,
    ) -> PvpPresentationStep:
        return PvpPresentationStep(message=" ".join(summary), event=structured)

    @staticmethod
    def _update_structured(
        event_data: PvpEvent | None,
        event: str,
        values: list[str],
    ) -> PvpEvent | None:
        if event_data is None:
            return event_data
        if event == "-supereffective":
            return replace(event_data, effectiveness="super effective")
        if event == "-resisted":
            return replace(event_data, effectiveness="not very effective")
        if event == "-crit":
            return replace(event_data, critical=True)
        if event == "-status" and len(values) >= 2:
            return replace(event_data, status=values[1].upper())
        if event == "faint":
            return replace(event_data, fainted=True)
        if event in {"-boost", "-unboost"} and len(values) >= 2:
            change = f"{values[1]} {'rose' if event == '-boost' else 'fell'}"
            return replace(event_data, stat_changes=(*event_data.stat_changes, change))
        return event_data

    def _translate_event(self, event: str, values: list[str]) -> str | None:
        if event == "-damage" and len(values) >= 2:
            return self._damage_text(values[0], values[1])
        if event == "-heal" and len(values) >= 2:
            return f"{_pokemon_name(values[0])} recovered HP."
        if event == "-status" and len(values) >= 2:
            return f"{_pokemon_name(values[0])} was afflicted with {values[1].upper()}."
        if event == "-curestatus" and len(values) >= 2:
            return f"{_pokemon_name(values[0])} was cured of {values[1].upper()}."
        if event == "-crit" and values:
            return f"A critical hit landed on {_pokemon_name(values[0])}."
        if event == "-supereffective":
            return "It was super effective."
        if event == "-resisted":
            return "It was not very effective."
        if event == "-immune" and values:
            return f"{_pokemon_name(values[0])} was immune."
        if event == "-fail" and values:
            return f"{_pokemon_name(values[0])}'s move failed."
        if event == "-miss" and values:
            return f"{_pokemon_name(values[0])}'s move missed."
        if event == "-protect" and values:
            return f"{_pokemon_name(values[0])} protected itself."
        if event == "-ability" and len(values) >= 2:
            return f"{_pokemon_name(values[0])}'s {values[1]} activated."
        if event in {"-boost", "-unboost"} and len(values) >= 2:
            verb = "rose" if event == "-boost" else "fell"
            return f"{_pokemon_name(values[0])}'s {values[1]} {verb}."
        if event == "switch" and len(values) >= 2:
            return (
                f"{_pokemon_name(values[0])} sent out {_safe_protocol_text(values[1])}."
            )
        if event == "faint" and values:
            return f"{_pokemon_name(values[0])} fainted."
        if event == "-weather" and values:
            return f"The weather changed to {values[0]}."
        if event == "-fieldstart" and values:
            return f"The field changed: {values[-1]}."
        if event == "win" and values:
            return f"{_safe_protocol_text(values[0])} won the battle."
        if event == "tie":
            return "The battle ended in a tie."
        return None

    def _damage_text(self, target: str, hp_value: str) -> str:
        name = _pokemon_name(target)
        current, maximum = _parse_hp(hp_value)
        key = _protocol_id(target)
        previous = self._last_hp.get(key)
        self._last_hp[key] = (current, maximum)
        if previous is not None and previous[0] >= current:
            damage = previous[0] - current
            return f"{name} took {damage} damage ({current}/{maximum} HP remaining)."
        return f"{name} is at {current}/{maximum} HP."


def _parse_hp(value: str) -> tuple[int, int]:
    match = re.match(r"\s*(\d+)\s*/\s*(\d+)", str(value))
    if match is None:
        return 0, 0
    return int(match.group(1)), int(match.group(2))


def _pokemon_name(value: str) -> str:
    """Remove only confirmed Showdown active-pokemon protocol prefixes."""
    text = str(value).strip()
    for prefix in ("p1a:", "p2a:"):
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def _protocol_id(value: str) -> str:
    text = _pokemon_name(value).lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def _safe_protocol_text(value: str) -> str:
    return _pokemon_name(value).replace("\r", " ").replace("\n", " ").strip()
