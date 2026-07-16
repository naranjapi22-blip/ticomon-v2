# Candy Shops

Use `!shop` to open the Technology Shop, Fossil Lab, or Pastry Shop. Choose a
product, review its GIF, price, relevant candy balances, and projected balance,
then confirm or cancel. Candy is not spent while previewing. Confirmation
performs the candy deduction and creature creation atomically; cancellation or
expiration changes nothing. Insufficient balances disable confirmation, and a
double click cannot create two purchases.

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
the purchase. The 8 technical/base variants without decoration are not shop
products.

## Persistence and deployment

Before using purchases in a new database, run:

```bash
python scripts/create_shop_schema.py
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

Prices are initial and may be adjusted using real economy data.
