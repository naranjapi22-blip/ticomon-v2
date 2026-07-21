# Candy Shops

Use `!shop` to open the Technology Shop, Fossil Lab, Pastry Shop, Garden, or
Pokémon Groomer. Choose a product, review its GIF, price, relevant candy
balances, and projected balance, then confirm or cancel. Candy is not spent
while previewing. Confirmation performs the candy deduction and creature
creation atomically; cancellation or expiration changes nothing. Insufficient
balances disable confirmation, and a double click cannot create two purchases.

All products show the exact creature GIF before confirmation. A missing asset
uses the existing fallback and does not block a purchase. The displayed
canonical variant is the variant delivered.

## Pricing model

Candies remain specific to each type and there is no universal currency. A
monotype creature pays the full category price in its type. A two-type creature
splits that fixed total between its two types; having two types does not double
the total cost. There are currently no discounts, rotations, dynamic prices,
or duplicate-price increases.

## Technology Shop

| Product | Price |
| --- | --- |
| Porygon | 60 Normal |
| Rotom | 40 Electric + 40 Ghost |
| Rotom Heat | 55 Electric + 55 Fire |
| Rotom Wash | 55 Electric + 55 Water |
| Rotom Mow | 55 Electric + 55 Grass |
| Golett | 45 Ground + 45 Ghost |

Rotom Frost and Rotom Fan are not currently available because canonical
variants and matching resources have not been confirmed. Historical `h`, `m`,
`w`, and `s` aliases are not shop products.

## Fossil Lab

| Product | Price |
| --- | --- |
| Omanyte | 60 Rock + 60 Water |
| Kabuto | 60 Rock + 60 Water |
| Aerodactyl | 60 Rock + 60 Flying |
| Lileep | 60 Rock + 60 Grass |
| Anorith | 60 Rock + 60 Bug |
| Cranidos | 120 Rock |
| Shieldon | 60 Rock + 60 Steel |
| Tirtouga | 60 Water + 60 Rock |
| Archen | 60 Rock + 60 Flying |
| Tyrunt | 75 Rock + 75 Dragon |
| Amaura | 75 Rock + 75 Ice |
| Dracozolt | 90 Electric + 90 Dragon |
| Arctozolt | 90 Electric + 90 Ice |
| Dracovish | 90 Water + 90 Dragon |
| Arctovish | 90 Water + 90 Ice |

Later evolutions are obtained through the normal evolution system, not bought
directly from the shop.

## Pastry Shop

Pastry Shop supports exactly 45 canonical Alcremie combinations: 9 creams × 5
decorations. The three purchase modes are:

| Mode | Price |
| --- | --- |
| Random cream and decoration | 60 Fairy |
| Selected cream, random decoration | 90 Fairy |
| Selected cream and decoration | 120 Fairy |

The combination is resolved before confirmation and is frozen for the GIF and
the purchase. The data also contains aliases without cream-name hyphens and
eight undecorated technical/base forms; none are shop products. No additional
decorations are supported by the verified canonical catalogue.

## Garden

Garden sells verified floral variants and collectible Vivillon patterns. Its
menu first separates Flabébé colors from Vivillon choices, so the pattern list
remains manageable.

### Flabébé

| Product | Price |
| --- | --- |
| Flabébé Blue | 45 Fairy |
| Flabébé Orange | 45 Fairy |
| Flabébé White | 45 Fairy |
| Flabébé Yellow | 45 Fairy |

Floette and Florges are not sold directly. A purchased color is retained by
the normal evolution flow when the destination species has the matching
canonical color. Eternal Floette is excluded.

### Vivillon

| Choice | Price |
| --- | --- |
| Random verified pattern | 35 Bug + 35 Flying |
| Selected verified pattern | 50 Bug + 50 Flying |

The selectable normal patterns are Archipelago, Continental, Elegant, Garden,
High Plains, Icy Snow, Jungle, Marine, Modern, Monsoon, Ocean, Polar, River,
Sandstorm, Savanna, Sun, and Tundra. Poké Ball is a special pattern and is not
sold. Fancy and other patterns without a canonical persisted variant and
confirmed resource are not offered.

## Pokémon Groomer

| Product | Price |
| --- | --- |
| Furfrou Natural | 45 Normal |
| Furfrou Dandy | 65 Normal |
| Furfrou Debutante | 65 Normal |
| Furfrou Diamond | 65 Normal |
| Furfrou Heart | 65 Normal |
| Furfrou Kabuki | 65 Normal |
| Furfrou La Reine | 65 Normal |
| Furfrou Matron | 65 Normal |
| Furfrou Pharaoh | 65 Normal |
| Furfrou Star | 65 Normal |

Each trim is delivered as the selected canonical variant. Groomer does not
change an existing Furfrou, apply a temporary trim, or perform automatic
reversions.

## Persistence and deployment

Before using purchases in a new database, run:

```bash
poetry run python scripts/create_shop_schema.py
```

The script is idempotent and creates `shop_purchase_receipts`, which stores
purchase idempotency keys. `trainer_id` and `creature_id` use PostgreSQL
`BIGINT`; candy deduction, receipt creation, and creature creation are one
transaction. If the schema is missing, the command reports:

```text
Shop schema is not initialized. Run scripts/create_shop_schema.py.
```

Purchased creatures enter the normal collection with a normal collection
number, generated IVs and size, a random original nature, no shiny status, and
`minted_nature = None`. Their later evolution uses the normal system.
Purchases also record the exact canonical species and variant in `!collections`,
so releasing or trading the creature later does not remove its themed-album
progress.

Prices are initial and may be adjusted using real economy data.
