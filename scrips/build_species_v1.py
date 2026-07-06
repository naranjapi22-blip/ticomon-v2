import requests

POKEMON_URL = "https://pokeapi.co/api/v2/pokemon/1/"
SPECIES_URL = "https://pokeapi.co/api/v2/pokemon-species/1/"


def fetch_pokemon():
    return requests.get(POKEMON_URL).json()


def fetch_species():
    return requests.get(SPECIES_URL).json()


def build_species_v1():
    pokemon = fetch_pokemon()
    species_data = fetch_species()

    species = {
        # identidad
        "pokeapi_id": pokemon["id"],
        "name": pokemon["name"],
        # clasificación
        "types": [t["type"]["name"] for t in pokemon["types"]],
        # mundo físico
        "height": pokemon["height"],
        "weight": pokemon["weight"],
        "display_scale": 1.0,
        # economía del juego (FUENTE REAL)
        "capture_rate": species_data["capture_rate"],
        "generation": int(species_data["generation"]["url"].rstrip("/").split("/")[-1]),
        "is_baby": species_data["is_baby"],
        "is_legendary": species_data["is_legendary"],
        "is_mythical": species_data["is_mythical"],
        # stats base
        "base_stats": {
            "hp": next(
                s["base_stat"] for s in pokemon["stats"] if s["stat"]["name"] == "hp"
            ),
            "attack": next(
                s["base_stat"]
                for s in pokemon["stats"]
                if s["stat"]["name"] == "attack"
            ),
            "defense": next(
                s["base_stat"]
                for s in pokemon["stats"]
                if s["stat"]["name"] == "defense"
            ),
            "special_attack": next(
                s["base_stat"]
                for s in pokemon["stats"]
                if s["stat"]["name"] == "special-attack"
            ),
            "special_defense": next(
                s["base_stat"]
                for s in pokemon["stats"]
                if s["stat"]["name"] == "special-defense"
            ),
            "speed": next(
                s["base_stat"] for s in pokemon["stats"] if s["stat"]["name"] == "speed"
            ),
        },
    }

    return species


def main():
    species = build_species_v1()

    print("\n=== SPECIES V1 COMPLETE (NEON READY) ===\n")
    for k, v in species.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
