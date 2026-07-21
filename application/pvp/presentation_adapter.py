from __future__ import annotations

from application.pvp.snapshots import PvpBattleSnapshot, PvpPokemonSnapshot
from rendering.battle.presentation_state import (
    BattlePresentationSide,
    BattlePresentationState,
)


def pvp_presentation_state(
    snapshot: PvpBattleSnapshot,
    *,
    player_name: str,
    opponent_name: str,
    last_event: str,
    waiting_text: str | None = None,
) -> BattlePresentationState:
    return BattlePresentationState(
        top=_side(
            snapshot.opponent_id,
            opponent_name,
            snapshot.opponent_active,
            snapshot.opponent_remaining,
        ),
        bottom=_side(
            snapshot.player_id,
            player_name,
            snapshot.player_active,
            snapshot.player_remaining,
        ),
        turn=snapshot.turn,
        last_event=last_event,
        terminal=snapshot.finished,
        winner_id=snapshot.winner_id,
        draw=snapshot.tie,
        waiting_text=waiting_text
        or ("Forced switch required" if snapshot.force_switch_player else None),
    )


def _side(
    trainer_id: int, name: str, pokemon: PvpPokemonSnapshot | None, remaining: int
) -> BattlePresentationSide:
    if pokemon is None:
        return BattlePresentationSide(
            trainer_id=trainer_id,
            display_name=name,
            active_name=None,
            sprite_identifier=None,
            capture_sprite_url=None,
            shiny=False,
            hp_current=0,
            hp_max=1,
            hp_fraction=0.0,
            status=None,
            fainted=False,
            remaining=remaining,
        )
    current = (
        pokemon.current_hp
        if pokemon.current_hp is not None
        else round(pokemon.hp_fraction * 100)
    )
    maximum = pokemon.max_hp if pokemon.max_hp is not None else 100
    return BattlePresentationSide(
        trainer_id=trainer_id,
        display_name=name,
        active_name=pokemon.species_name,
        sprite_identifier=pokemon.sprite_identifier,
        capture_sprite_url=pokemon.capture_sprite_url,
        shiny=pokemon.shiny,
        hp_current=current,
        hp_max=maximum,
        hp_fraction=pokemon.hp_fraction,
        status=pokemon.status,
        fainted=pokemon.fainted,
        remaining=remaining,
    )
