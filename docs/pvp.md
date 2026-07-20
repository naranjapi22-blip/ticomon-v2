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

The current Discord slice implements challenge lifecycle and loadout
conversion. Accepting the preliminary `!pvp` challenge ends the session with a
controlled message; no battle is started yet. Action resolution, forced
switches, and specialized protocol presentation remain follow-up work. No
Showdown server, FFmpeg, animation, ranking, or history is introduced here.
