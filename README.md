# TicoMon V2

> A Pokémon-inspired monster collecting game powered by a modular game engine.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Status](https://img.shields.io/badge/Status-Beta-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## About

TicoMon V2 is a monster collecting game built for Discord.

Unlike traditional Discord bots, TicoMon is designed as a standalone game engine where Discord is only the first user interface. The project focuses on clean architecture, domain-driven design, and long-term maintainability.

Players can discover wild Pokémon, capture them, collect Candies, evolve their team, complete the Pokédex, and customize their collection with cosmetic variants and regional forms.

---

## Getting Started

- Install dependencies with `poetry install`.
- Run the bot with `poetry run python main.py`.

For validation before pushing changes:

- `poetry run ruff check .`
- `poetry run black --check .`
- `poetry run pytest -q`
- `python scripts/check_all.py` runs the test suite only.

Battle uses local Gen 9 simulation via `poke-env` (damage calc and learnsets only — no Showdown server). Battle challenge sessions are in-memory and do not survive bot restarts.

---

## Features

- 🎯 Wild Pokémon encounters
- ⚡ Energy system
- 🍬 Candy economy
- 🌱 Evolution system
- 📖 Pokédex
- 👤 Trainer profiles
- ❤️ Favorite Pokémon
- ✨ Cosmetic variants
- 🌍 Regional forms
- 📦 Duplicate management
- 🎲 Dynamic capture chances
- 🖼️ Animated capture sequences
- 🤝 Trading
- ⚔️ PvP Battles
- 🦁 Safari
- 🌿 Nature Mints
- 🏆 Thematic Collections

---

## Gameplay Loop

```text
Choose your Trainer
        ↓
Use !spawn
        ↓
Encounter Pokémon
        ↓
Capture Pokémon
        ↓
Collect Candies
        ↓
Evolve your team
        ↓
Complete your Pokédex
```

## Nature Mints

TicoMon has one universal Nature Mint. Use `!mint <collection_number>` to
choose a valid statistical nature effect for a creature. The creature's
original nature remains intact; replacing its current effect or restoring the
original effect consumes one mint. Selecting the effect already in use does
not consume a mint. Nature Mints are currently awarded through achievements.

## Achievements

Achievements award Candies and Nature Mints across early, mid, and advanced
progression. Progress is integrated with captures, unique species discovered,
Safari captures, shiny, legendary, mythical, trade, and evolution activities.

## Thematic Collections

Use `!collections` to review six themed albums: Fossil Restoration, Technology,
Alcremie, Vivillon Patterns, Furfrou Styles, and Flabébé Garden. Collection
progress is historical: an entry remains collected after a creature is released
or traded. Claiming a milestone also requires currently owning enough distinct
entries for that threshold. Completed milestones can be claimed once for type
Candies and Nature Mints. See [Collections](docs/collections.md) for the album
entries, rewards, backfill, and historical limitations.

## Shops

Use `!shop` to spend type-specific Candies in the Technology Shop, Fossil Lab,
Pastry Shop, Garden, or Pokémon Groomer. The catalogue provides special species
and verified cosmetic variants that do not appear in normal Spawn or Safari.
Every product shows its exact GIF before confirmation; the preview does not
spend candies. Purchases are atomic and create a normal, non-shiny creature
with generated IVs and size, random original nature, and no Nature Mint effect.
Garden offers verified Flabébé colors and normal Vivillon patterns, while
Pokémon Groomer offers Furfrou and its confirmed trims. The supported Alcremie
catalogue contains 45 combinations: 9 creams and 5 decorations. Rotom Frost
and Rotom Fan are temporarily excluded until their canonical variants and
graphic resources are confirmed.

Shop prices are initial values and can be adjusted later using real economy
metrics; there are no dynamic prices or universal currency.

## Safari

Safari expeditions use shared maps, routes, weather, and encounters. Players
choose routes with visible buttons and vote on the available routes; a vote can
be replaced before the route vote closes. Captures are personal while the
encounter populations are shared. Shiny, legendary, and mythical encounters
are unique specimens. Players select Safari Balls during encounters and can
view the final expedition summary.

---

## Architecture

TicoMon follows a modular architecture centered around an independent Core.

```text
Discord
    │
    ▼
Application
    │
    ▼
Core
    │
    ▼
Repositories
```

The Core contains all gameplay rules and has no dependency on Discord. This allows the game to grow independently from its user interface and makes future clients, such as web or mobile applications, possible.

---

## Project Structure

```text
application/
core/
interfaces/
rendering/
scripts/
test/
```

---

## Tech Stack

- Python 3.11
- discord.py
- PostgreSQL
- Railway
- Cloudflare R2
- PokéAPI
- Pillow

---

## Current Status

**Version:** Beta

### Implemented

- ✅ Species
- ✅ Spawn
- ✅ Opportunity
- ✅ Capture
- ✅ Reward
- ✅ Energy
- ✅ Candy
- ✅ Evolution
- ✅ Release
- ✅ Trainer
- ✅ Trainer Profiles
- ✅ Onboarding
- ✅ Pokédex
- ✅ Cosmetic Variants
- ✅ Regional Forms
- ✅ Duplicate Management

### Integrated and available

- ✅ Trading
- ✅ Safari
- ✅ Achievements
- ✅ Nature Mints
- ✅ Candy shops
- ✅ Thematic collections

The core gameplay loop is complete.

### In development or pending release

- ⚔️ PvP Battles
- 👥 Raids

### Planned

- 📅 Daily Quests
- 🎉 Seasonal Events
- 🥇 Competitive Rankings

---

## Roadmap

Future updates focus on the systems listed above under development or planned.

---

## Design Philosophy

TicoMon is built around a few core principles:

- The Core never depends on Discord.
- Every piece of data has a single source of truth.
- Each module owns a single responsibility.
- The architecture adapts to the domain, not the other way around.
- Gameplay systems should remain reusable and testable.

---

## Documentation

The project's architecture and design principles are documented in the **Architecture Design Document (ADD)**.

The ADD explains the philosophy, responsibilities, and decisions behind the architecture used throughout the project.

Safari-specific user, development, and operations notes live in `docs/safari.md`.
Spawn and Safari sessions are in memory; a bot restart clears active sessions and active registrations.
Persistent data such as trainers, creatures, rewards, and progress remains in PostgreSQL.

---

## License

This project is licensed under the MIT License.
