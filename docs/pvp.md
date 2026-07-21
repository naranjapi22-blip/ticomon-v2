# Fast PvP

The current fast PvP flow is registered as `!pvp @trainer`. It has its own
in-memory session registry and does not reuse or modify the legacy `!battle`
cog, views, or execution service. `!moves <collection>` displays a persisted
moveset; `!moves <collection> <slot> <move>` replaces a slot after validating
the Gen 9 Showdown learnset.

## Implemented flow

Fast PvP currently provides:

- challenge acceptance and private 3v3 team selection;
- persisted ability, IV, effective nature, and equipped-move validation;
- private legal move and switch actions;
- forced switches, forfeits, victory and defeat completion;
- 15-second move timeouts and 10-second forced-switch timeouts;
- compact protocol translation and in-memory session cleanup;
- a public board updated in place from structured battle snapshots.

The board presents active HP, status, knockouts, remaining team members,
forced-switch state, turn information, and the final winner or terminal result.
It resolves front/back and shiny sprites through the R2-backed rendering
helpers. It does not retain a permanent event history.

## Battle authority and format

The controller uses two human-controlled `poke-env` players connected to a
reachable Pokemon Showdown server over WebSocket. `poke-env` is the client and
protocol adapter; Showdown owns PP, battle effects, and live battle state.
Local development can use these endpoints when a Showdown server is running
in the same machine:

```text
SHOWDOWN_WEBSOCKET_URL=ws://localhost:8000/showdown/websocket
# Optional for a private server with passwordless accounts.
SHOWDOWN_AUTHENTICATION_URL=
```

The controller rejects these implicit localhost defaults at startup. Production
must set `SHOWDOWN_WEBSOCKET_URL` explicitly to the reachable Showdown service
URL. The current Railway worker example uses the private network:

```text
SHOWDOWN_WEBSOCKET_URL=ws://pokemon-showdown.railway.internal:8080/showdown/websocket
```

TicoMon does not create or start the Showdown worker. Do not replace the
private hostname with a public URL when the Railway services can communicate
over the private network. `SHOWDOWN_AUTHENTICATION_URL` is optional for the
current passwordless private-server flow. Set it to an `http://` or `https://`
authentication endpoint only when the configured Showdown authentication flow
requires one.

The technical format is Gen 9 custom game at level 50, with zero EVs,
persisted IVs, effective nature, persisted ability, four equipped moves, and
no item. No special mechanics, ranking, rewards, or permanent PvP history are
currently introduced. The flow does not use the local legacy battle simulator
as its live battle authority.

`!battle` remains a separate legacy command and is not replaced or modified by
fast PvP.

## Loadout setup

Run these idempotent scripts for a database that has not yet received the
creature loadout columns and catalog:

```powershell
poetry run python scripts/create_creature_loadout_schema.py
poetry run python scripts/sync_creature_loadout_catalog.py --dry-run
poetry run python scripts/sync_creature_loadout_catalog.py
poetry run python scripts/migrate_creature_loadouts.py --dry-run
poetry run python scripts/migrate_creature_loadouts.py
```

The scripts use `NEON_DATABASE_URL`. The migration preserves valid existing
values, assigns deterministic catalog defaults when needed, reports missing
catalogs, and is safe to rerun. Review the dry-run output before applying it.

Initial moves are selected deterministically from the installed Gen 9
`poke-env` catalog and are limited to four. A non-empty configured moveset is
not replaced automatically.

## Local Showdown

Install the official server outside this repository and start it from its
checkout:

```powershell
git clone https://github.com/smogon/pokemon-showdown.git
cd pokemon-showdown
npm install
node pokemon-showdown start --no-security
```

The expected local endpoint is `ws://localhost:8000/showdown/websocket`.
`localhost` is accepted only when it is explicitly configured for local
development; it is not an implicit production fallback.

Run the non-Discord diagnostic with:

```powershell
poetry run python -m scripts.diagnose_pvp_showdown
```

The local integration test uses the `showdown_local` marker and skips when a
reachable local Showdown server is not available:

```powershell
poetry run pytest -q -m showdown_local
```

Unit tests use injected controller and session doubles and do not contact
Discord or Showdown.
