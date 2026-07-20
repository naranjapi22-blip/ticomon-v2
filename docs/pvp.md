# Fast PvP

The fast PvP flow is registered as `!pvp @trainer`. It has its own in-memory
session registry and does not reuse the legacy `!battle` cog, views, or
execution service. `!moves <collection>` displays the persisted moveset;
`!moves <collection> <slot> <move>` replaces a slot after validating the Gen 9
Showdown learnset.

Run the idempotent schema setup before starting the bot:

```powershell
poetry run python scripts/create_creature_loadout_schema.py
poetry run python scripts/sync_creature_loadout_catalog.py --dry-run
poetry run python scripts/sync_creature_loadout_catalog.py
poetry run python scripts/migrate_creature_loadouts.py --dry-run
poetry run python scripts/migrate_creature_loadouts.py
```

The scripts use `NEON_DATABASE_URL` from the project environment. The bot
also requires the existing `DISCORD_TOKEN`; no new environment variable is
introduced.

The migration keeps valid existing values, assigns the first sorted catalog
ability when the stored value is missing or invalid, reports missing catalogs,
and is safe to rerun. Initial moves use the sorted Gen 9 catalog and stable
move ids as tie-breakers. Review the dry-run summary before production. To
revert before applying the migration, restore a database snapshot; no
destructive rollback is included because existing creature data must not be
deleted.

Gen 9 data comes from the installed `poke-env` Showdown data, including
canonical names and species learnsets. The initial ability rule is stable
catalog order: an existing valid ability is preserved; otherwise the first
catalog ability is assigned. Initial moves are sorted deterministically by
offensive/STAB suitability and id, limited to four, and never replace a
non-empty configured moveset. Missing catalogs are reported and never invented.

The fast PvP flow now implements challenge acceptance, private 3v3 selection,
loadout validation, manual `poke-env` players, private legal actions, 15-second
move timeouts, 10-second forced-switch timeouts, forfeits, compact protocol
translation, and in-memory cleanup. The controller uses two human-controlled
`poke-env` players and requires a reachable Pokémon Showdown server using the
configured `poke-env` server configuration (the default is local Showdown on
`ws://localhost:8000/showdown/websocket`).

The technical battle format is Gen 9 at level 50, with zero EVs, persisted IVs,
effective nature, persisted ability, four equipped moves, and no item. PP and
all battle effects remain owned by Showdown. The Discord board edits one public
message and does not retain a visible event history. No FFmpeg, animation,
ranking, rewards, or permanent PvP history is introduced.

`!battle` remains a separate legacy flow. The manual PvP controller is not a
fallback to the legacy simulator. A local manual run requires the existing bot
environment plus a local Pokémon Showdown server; unit tests use injected
session/controller doubles and do not contact Discord or Showdown.
