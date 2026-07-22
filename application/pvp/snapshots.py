from __future__ import annotations

from dataclasses import dataclass

from application.pvp.models import PvpEvent
from rendering.battle.pvp_sprite_urls import showdown_sprite_identifier


@dataclass(frozen=True)
class PvpPokemonSnapshot:
    species_name: str
    form_name: str | None
    current_hp: int | None
    max_hp: int | None
    hp_fraction: float
    status: str | None
    fainted: bool
    sprite_identifier: str | None = None
    capture_sprite_url: str | None = None
    shiny: bool = False


@dataclass(frozen=True)
class PvpBattleSnapshot:
    turn: int
    player_id: int
    opponent_id: int
    player_active: PvpPokemonSnapshot | None
    opponent_active: PvpPokemonSnapshot | None
    player_remaining: int
    opponent_remaining: int
    force_switch_player: bool
    force_switch_opponent: bool
    finished: bool
    winner_id: int | None
    tie: bool
    player_team: tuple[PvpPokemonSnapshot, ...] = ()
    opponent_team: tuple[PvpPokemonSnapshot, ...] = ()
    last_decisive_event: PvpEvent | None = None
    last_decisive_event_turn: int | None = None


def snapshot_battle(
    battle,
    *,
    player_id: int,
    opponent_id: int,
    capture_sprite_urls: dict[tuple[str, bool], str] | None = None,
) -> PvpBattleSnapshot:
    player_team = tuple(battle.team.values())
    opponent_team = tuple(battle.opponent_team.values())
    winner_id = None
    if battle.won:
        winner_id = player_id
    elif battle.lost:
        winner_id = opponent_id
    return PvpBattleSnapshot(
        turn=int(getattr(battle, "turn", 0) or 0),
        player_id=player_id,
        opponent_id=opponent_id,
        player_active=_pokemon_snapshot(
            getattr(battle, "active_pokemon", None),
            capture_sprite_urls=capture_sprite_urls,
        ),
        opponent_active=_pokemon_snapshot(
            getattr(battle, "opponent_active_pokemon", None),
            capture_sprite_urls=capture_sprite_urls,
        ),
        player_remaining=sum(not pokemon.fainted for pokemon in player_team),
        opponent_remaining=sum(not pokemon.fainted for pokemon in opponent_team),
        force_switch_player=bool(getattr(battle, "force_switch", False)),
        force_switch_opponent=bool(getattr(battle, "_opponent_force_switch", False)),
        finished=bool(getattr(battle, "finished", False)),
        winner_id=winner_id,
        tie=bool(getattr(battle, "finished", False))
        and not bool(getattr(battle, "won", False))
        and not bool(getattr(battle, "lost", False)),
        player_team=tuple(
            _pokemon_snapshot(
                pokemon,
                capture_sprite_urls=capture_sprite_urls,
            )
            for pokemon in player_team
        ),
        opponent_team=tuple(
            _pokemon_snapshot(
                pokemon,
                capture_sprite_urls=capture_sprite_urls,
            )
            for pokemon in opponent_team
        ),
    )


def _pokemon_snapshot(
    pokemon,
    *,
    capture_sprite_urls: dict[tuple[str, bool], str] | None = None,
) -> PvpPokemonSnapshot | None:
    if pokemon is None:
        return None
    status = getattr(pokemon, "status", None)
    status_name = None
    if status is not None:
        if isinstance(status, str):
            status_name = status
        else:
            status_name = getattr(status, "name", None) or getattr(
                status, "value", None
            )
        status_name = str(status_name).upper()
    species_value = getattr(pokemon, "species", None)
    species_identifier = getattr(species_value, "identifier", None)
    species_name = str(species_value or getattr(pokemon, "name", "Unknown"))
    sprite_identifier = showdown_sprite_identifier(
        species_name,
        getattr(pokemon, "forme", None),
        species_identifier,
    )
    shiny = bool(getattr(pokemon, "is_shiny", False))
    current_hp = getattr(pokemon, "current_hp", None)
    fainted = bool(getattr(pokemon, "fainted", False)) or current_hp == 0
    if fainted:
        status_name = "FNT"
        current_hp = 0
    return PvpPokemonSnapshot(
        species_name=species_name,
        form_name=getattr(pokemon, "forme", None),
        current_hp=current_hp,
        max_hp=getattr(pokemon, "max_hp", None),
        hp_fraction=(
            0.0
            if fainted
            else float(getattr(pokemon, "current_hp_fraction", 0.0) or 0.0)
        ),
        status=status_name,
        fainted=fainted,
        sprite_identifier=sprite_identifier,
        capture_sprite_url=(capture_sprite_urls or {}).get((sprite_identifier, shiny)),
        shiny=shiny,
    )
