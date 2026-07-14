from __future__ import annotations

import requests
from core.evolution.stage_resolver import StageResolver

from core.spawn.spawn_rarity_classifier import SpawnRarityClassifier

BASE_URL = "https://pokeapi.co/api/v2"

session = requests.Session()


def fetch_pokemon(pokemon_id: int) -> dict:
    response = session.get(
        f"{BASE_URL}/pokemon/{pokemon_id}",
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def fetch_species(pokemon_id: int) -> dict:
    response = session.get(
        f"{BASE_URL}/pokemon-species/{pokemon_id}",
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def fetch_evolution_chain(url: str) -> dict:
    response = session.get(
        url,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def build_species(pokemon_id: int) -> dict:
    pokemon = fetch_pokemon(pokemon_id)
    species = fetch_species(pokemon_id)

    evolution_chain = fetch_evolution_chain(species["evolution_chain"]["url"])

    stats = {stat["stat"]["name"]: stat["base_stat"] for stat in pokemon["stats"]}

    base_stat_total = sum(stats.values())

    stage_resolver = StageResolver()
    classifier = SpawnRarityClassifier()

    evolution_stage = stage_resolver.resolve(
        chain=evolution_chain,
        species_name=pokemon["name"],
    )

    spawn_rarity = classifier.classify(
        capture_rate=species["capture_rate"],
        base_stat_total=base_stat_total,
        is_legendary=species["is_legendary"],
        is_mythical=species["is_mythical"],
        evolution_stage=evolution_stage,
    )

    generation = int(species["generation"]["url"].rstrip("/").split("/")[-1])

    return {
        # Identity
        "pokeapi_id": pokemon["id"],
        "name": pokemon["name"],
        # Gameplay
        "types": [t["type"]["name"] for t in pokemon["types"]],
        "height": pokemon["height"],
        "weight": pokemon["weight"],
        "display_scale": 1.0,
        # Metadata
        "capture_rate": species["capture_rate"],
        "spawn_rarity": spawn_rarity.value,
        "generation": generation,
        "is_baby": species["is_baby"],
        "is_legendary": species["is_legendary"],
        "is_mythical": species["is_mythical"],
        # Base stats
        "base_stats": {
            "hp": stats["hp"],
            "attack": stats["attack"],
            "defense": stats["defense"],
            "special_attack": stats["special-attack"],
            "special_defense": stats["special-defense"],
            "speed": stats["speed"],
        },
    }


def main():
    species = build_species(3)

    print("\n=== SPECIES BUILDER ===\n")

    for key, value in species.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
