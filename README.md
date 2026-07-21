# TicoMon V2

TicoMon is a Pokemon-inspired collecting game engine whose first interface is
Discord. Discord is an adapter around the game, not the game domain itself.

The project is structured so that the Core can be tested without Discord,
PostgreSQL, Railway, or external battle services. PostgreSQL on Neon is the
persistent source of truth for trainers, creatures, progression, inventories,
and game history. Cloudflare R2 serves the public GIF and sprite resources.
Pokemon data is derived primarily from PokéAPI, while the current fast PvP
flow uses Pokemon Showdown through `poke-env` and its WebSocket protocol.

## Current status

TicoMon V2 has a working gameplay loop and multiple integrated game systems.

- **Implemented:** the systems described under Gameplay systems, including
  fast PvP and atomic multi-creature release.
- **Integrated:** Discord adapters, Neon persistence, R2 presentation assets,
  Safari, trading, shops, Collections, achievements, and shared battle
  presentation.
- **Experimental or operationally local:** live PvP requires a reachable
  Pokemon Showdown WebSocket server. Active Spawn, Safari, and PvP sessions
  are in memory and do not survive a bot restart.
- **Not currently committed:** raids, daily quests, seasonal events,
  competitive rankings, and permanent PvP history.

## Gameplay systems

- Spawn opportunities and capture, including capture chances, balls, IVs,
  natures, sizes, shiny encounters, and animated GIF presentation.
- Trainer energy and type-specific Candy inventories.
- Evolution with persisted creature identity, original nature, forms, and
  collection history.
- Individual and multiple creature release. The production release path uses
  a `ReleaseUnitOfWork` so creature deletion and Candy persistence commit or
  roll back together.
- Batch duplicate management with bounded species and variant loading, avoiding
  per-species N+1 queries.
- Pokédex discovery, trainer profiles, favorites, IV inspection, original
  natures, and Nature Mints.
- Persisted abilities and equipped moves, managed with `!moves`.
- Cosmetic variants, regional forms, shiny creatures, and fallback graphics.
- Trading, Safari expeditions, achievements, historical Collections, Candy
  Shops, and trainer teams.
- Fast private 3v3 PvP using persisted abilities, moves, IVs, and effective
  natures.

## Fast PvP

The current PvP command is `!pvp @trainer`. It is separate from the legacy
`!battle` command, which remains unchanged.

PvP provides private 3v3 team selection, persisted loadout validation, legal
move and switch selection, forced switches, forfeits, move and forced-switch
timeouts, victory/defeat completion, and controlled cleanup. The battle engine
uses two `poke-env` players connected to a Pokemon Showdown server over
WebSocket. It does not use a local-only damage simulator as the live battle
authority.

The public Discord board is updated in place from structured Showdown battle
snapshots. It presents front/back and shiny sprites from R2, active HP and
status, knockouts, remaining creatures, turn information, and the final
winner or terminal result. There is no competitive ranking or permanent PvP
history yet.

See [docs/pvp.md](docs/pvp.md) for the battle format, Showdown setup, loadout
migration, environment variables, and local diagnostics.

## Release and duplicate management

The production release service is wired by `build_core()` with
`NeonReleaseUnitOfWork`. A release transaction uses one PostgreSQL connection
and transaction to:

1. Validate and lock the requested creatures in stable collection-number
   order.
2. Lock the trainer's Candy inventory once.
3. Calculate all rewards before deleting anything.
4. Delete the creatures in one batch, always filtered by `trainer_id`.
5. Persist the grouped type-specific Candy inventory.

Any failure rolls back both creature deletion and Candy changes. Duplicate
management similarly retrieves species with batch operations and loads only
variants belonging to the species actually recovered.

See [docs/release.md](docs/release.md) for the application and persistence
boundary details.

## Installation and development

TicoMon targets Python 3.11 or newer and supports Python versions below 4.0.
The repository uses Poetry and is configured as a non-package application:

```powershell
poetry install --no-interaction
poetry run python main.py
```

The bot requires a Discord token and a Neon PostgreSQL connection string. Put
local values in `.env`; do not commit secrets:

```text
DISCORD_TOKEN=your-discord-token
NEON_DATABASE_URL=your-neon-connection-string
```

The live PvP flow also requires a reachable Pokemon Showdown WebSocket server.
The defaults are:

```text
SHOWDOWN_WEBSOCKET_URL=ws://localhost:8000/showdown/websocket
SHOWDOWN_AUTHENTICATION_URL=http://localhost:8000/action.php?
```

See [docs/pvp.md](docs/pvp.md) for installing and starting the external
Showdown server. No FFmpeg installation is required by the current production
GIF and battle presentation paths.

### Validation

```powershell
poetry run black --check .
poetry run ruff check .
poetry run pytest -q -m "not neon_db"
git diff --check
```

Neon tests require `NEON_DATABASE_URL` and can be run explicitly with:

```powershell
poetry run pytest -q -m neon_db
```

CI runs Black and Ruff, the `not neon_db` unit suite, and Neon tests only when
the CI secret is available. `poetry run python scripts/check_all.py` runs the
test suite only.

## Project structure

```text
core/           Domain rules, entities, value objects, and ports. No Discord
                or persistence dependencies.
application/    Use-case orchestration and application services.
infrastructure/ Neon/PostgreSQL repositories, Showdown integration, and
                external service implementations.
interfaces/     Discord commands, views, buttons, and interaction adapters.
rendering/      GIF, sprite, battle, and other presentation resource helpers.
simulation/     Safari and gameplay simulation tools outside the domain.
scripts/        Schema, import, migration, catalog, and diagnostic utilities.
docs/           Public gameplay, operations, and architecture notes.
test/           Layered unit, integration, rendering, and infrastructure tests.
```

Dependencies point toward the Core. The Core returns domain results rather
than Discord embeds or components, and each datum has one source of truth.
Normal Spawn and Safari share the opportunity model while retaining their
distinct interaction rules.

## Documentation

- [PvP](docs/pvp.md) - Showdown integration, loadouts, snapshots, and the
  public battle board.
- [Release and duplicate management](docs/release.md) - Atomic release
  persistence and bounded duplicate queries.
- [Candy economy](docs/candies.md) - Type-specific Candy rules.
- [Thematic Collections](docs/collections.md) - Albums, historical progress,
  claims, and schema setup.
- [Safari](docs/safari.md) - Player flow, development boundaries, and
  operations.
- [Candy Shops](docs/shops.md) - Catalogues, pricing, and purchase
  persistence.
- [Architecture Design Document](Architecture%20Design%20Document%20(ADD).docx)
  - Domain and architecture decisions.

## Design principles

- The Core never depends on Discord, PostgreSQL, or external infrastructure.
- Every piece of data has a single source of truth.
- Each module owns a focused responsibility.
- Application services coordinate use cases; infrastructure implements ports.
- Presentation code renders domain results but does not own game rules.

## License

This project is licensed under the MIT License.
