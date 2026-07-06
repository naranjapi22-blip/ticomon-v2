from __future__ import annotations

import requests

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


def build_species(pokemon_id: int) -> dict:
    pokemon = fetch_pokemon(pokemon_id)
    species = fetch_species(pokemon_id)

    stats = {stat["stat"]["name"]: stat["base_stat"] for stat in pokemon["stats"]}

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
    species = build_species(1)

    print("\n=== SPECIES BUILDER ===\n")

    for key, value in species.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
