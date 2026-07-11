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
tests/
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

### Completed Systems

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

The core gameplay loop is complete.

---

## Roadmap

Future updates include:

- ⚔️ PvP Battles
- 🤝 Trading
- 🏆 Achievements
- 📅 Daily Quests
- 🎉 Seasonal Events
- 🦁 Safari 2.0
- 👥 Raids
- 🥇 Competitive Rankings

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

---

## License

This project is licensed under the MIT License.
