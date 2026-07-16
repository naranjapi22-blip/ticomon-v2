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
| Porygon | 80 Normal |
| Rotom | 50 Electric + 50 Ghost |
| Rotom Heat | 70 Electric + 70 Fire |
| Rotom Wash | 70 Electric + 70 Water |
| Rotom Mow | 70 Electric + 70 Grass |
| Golett | 60 Ground + 60 Ghost |

Rotom Frost and Rotom Fan are not currently available because canonical
variants and matching resources have not been confirmed. Historical `h`, `m`,
`w`, and `s` aliases are not shop products.

## Fossil Lab

| Product | Price |
| --- | --- |
| Omanyte | 80 Rock + 80 Water |
| Kabuto | 80 Rock + 80 Water |
| Aerodactyl | 80 Rock + 80 Flying |
| Lileep | 80 Rock + 80 Grass |
| Anorith | 80 Rock + 80 Bug |
| Cranidos | 160 Rock |
| Shieldon | 80 Rock + 80 Steel |
| Tirtouga | 80 Water + 80 Rock |
| Archen | 80 Rock + 80 Flying |
| Tyrunt | 100 Rock + 100 Dragon |
| Amaura | 100 Rock + 100 Ice |
| Dracozolt | 110 Electric + 110 Dragon |
| Arctozolt | 110 Electric + 110 Ice |
| Dracovish | 110 Water + 110 Dragon |
| Arctovish | 110 Water + 110 Ice |

Later evolutions are obtained through the normal evolution system, not bought
directly from the shop.

## Pastry Shop

Pastry Shop supports exactly 45 canonical Alcremie combinations: 9 creams × 5
decorations. The three purchase modes are:

| Mode | Price |
| --- | --- |
| Random cream and decoration | 80 Fairy |
| Selected cream, random decoration | 120 Fairy |
| Selected cream and decoration | 160 Fairy |

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
