# Thematic Collections

Use `!collections` to browse themed albums, review collected and missing
entries, and claim each completed milestone once. Progress is historical: a
canonical species or variant counts after it has been obtained, even if the
creature is later released or traded away. Trading legitimately obtained
creatures counts historically; no `original_trainer_id` restriction, holding
period, or loan lock applies.

Collection entries are recorded for starters, normal captures, Safari captures,
Shop purchases, successful evolutions, and received trades. A missing GIF uses
the normal graphic fallback and never changes progress.

## Claiming rewards

Choose an available `Claim Reward` button after reaching its threshold. The
system recalculates historical progress and the current collection. A `N`
entry milestone requires both historical progress of `N` and currently owning
`N` distinct valid entries from that album; duplicate copies do not increase
the owned count. It then records the claim, grants type-specific Candies and
Nature Mints, and commits them as one transaction. A claim is idempotent:
double clicks, concurrent requests, and retries cannot grant it twice.

The interface distinguishes `✅ Obtained and currently owned`, `◉ Obtained
historically, not currently owned`, and `❌ Never obtained`. It makes clear
when historical progress is complete but the current ownership requirement
prevents claiming. The preview and navigation never grant rewards. Cancelling
or letting a view expire changes nothing.

## Albums

### Fossil Restoration

Entries: Omanyte, Kabuto, Aerodactyl, Lileep, Anorith, Cranidos, Shieldon,
Tirtouga, Archen, Tyrunt, Amaura, Dracozolt, Arctozolt, Dracovish, and
Arctovish.

| Progress | Reward |
| --- | --- |
| 5 / 15 | 20 Rock Candies |
| 10 / 15 | 30 Rock Candies |
| 15 / 15 | 50 Rock Candies + 1 Nature Mint |

### Technology Collection

Entries: Porygon, Rotom, Rotom Heat, Rotom Wash, Rotom Mow, and Golett. Rotom
Frost and Rotom Fan remain excluded because their canonical variants and assets
are not yet verified.

| Progress | Reward |
| --- | --- |
| 3 / 6 | 20 Electric + 20 Normal Candies |
| 6 / 6 | 30 Electric + 30 Ghost Candies + 1 Nature Mint |

### Alcremie Collection

The album contains the 45 canonical decorated combinations: 9 creams × 5
decorations. It excludes aliases, undecorated technical/base rows, and shiny
creatures.

| Progress | Reward |
| --- | --- |
| 5 / 45 | 20 Fairy Candies |
| 15 / 45 | 40 Fairy Candies |
| 30 / 45 | 60 Fairy Candies + 1 Nature Mint |
| 45 / 45 | 100 Fairy Candies + 2 Nature Mints |

### Vivillon Patterns

The album includes 17 verified normal patterns. Poké Ball Pattern, Fancy
Pattern, aliases, technical variants, and shiny creatures are excluded.

| Progress | Reward |
| --- | --- |
| 5 / 17 | 20 Bug + 20 Flying Candies |
| 10 / 17 | 30 Bug + 30 Flying Candies |
| 17 / 17 | 50 Bug + 50 Flying Candies + 1 Nature Mint |

### Furfrou Styles

Entries are Natural plus the nine canonical trims: Dandy, Debutante, Diamond,
Heart, Kabuki, La Reine, Matron, Pharaoh, and Star.

| Progress | Reward |
| --- | --- |
| 5 / 10 | 30 Normal Candies |
| 10 / 10 | 60 Normal Candies + 1 Nature Mint |

### Flabébé Garden

The album tracks the complete Flabébé, Floette, and Florges line in Blue,
Orange, White, and Yellow. Eternal Floette and every Eternal, alias, or
technical variant are excluded. Normal evolution keeps a matching canonical
flower color, so each stage is collected through the usual evolution system.

| Progress | Reward |
| --- | --- |
| 4 / 12 | 20 Fairy Candies |
| 8 / 12 | 40 Fairy Candies |
| 12 / 12 | 60 Fairy Candies + 1 Nature Mint |

## Existing collections and deployment

Run the following once for every new database before using Collections:

```bash
python scripts/create_collection_schema.py
```

The script is idempotent. It creates the historical entry table and the
idempotent claim table, using `BIGINT` for trainer and species identifiers.
If the schema is missing, the command reports:

```text
Collections schema is not initialized. Run scripts/create_collection_schema.py.
```

Run this separate, idempotent backfill after the schema exists to record the
creatures currently owned by trainers:

```bash
python scripts/backfill_collection_entries.py
```

The backfill never changes creatures or grants rewards automatically. A
creature obtained and released before Collections existed cannot be recovered
unless another safe historical source already records its exact canonical
variant; current achievements record species-level facts only, so they cannot
reconstruct those historical variants.
