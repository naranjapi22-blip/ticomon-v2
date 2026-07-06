import psycopg2


def get_connection():
    return psycopg2.connect(
        host="YOUR_NEON_HOST",
        database="YOUR_DB",
        user="YOUR_USER",
        password="YOUR_PASSWORD",
        sslmode="require",
    )


def insert_species(conn, species):
    cur = conn.cursor()

    # separar types
    types = species["types"]
    type_1 = types[0] if len(types) > 0 else None
    type_2 = types[1] if len(types) > 1 else None

    stats = species["base_stats"]

    cur.execute(
        """
        INSERT INTO species (
            pokeapi_id, name,
            type_1, type_2,
            height, weight, display_scale,
            capture_rate, is_legendary, is_mythical,
            hp, attack, defense,
            special_attack, special_defense, speed
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (pokeapi_id) DO NOTHING
    """,
        (
            species["pokeapi_id"],
            species["name"],
            type_1,
            type_2,
            species["height"],
            species["weight"],
            species["display_scale"],
            species["capture_rate"],
            species["is_legendary"],
            species["is_mythical"],
            stats["hp"],
            stats["attack"],
            stats["defense"],
            stats["special_attack"],
            stats["special_defense"],
            stats["speed"],
        ),
    )

    cur.close()


def main():
    # 👇 ESTE ES TU OUTPUT YA VALIDADO
    species = {
        "pokeapi_id": 1,
        "name": "bulbasaur",
        "types": ["grass", "poison"],
        "height": 7,
        "weight": 69,
        "display_scale": 1.0,
        "capture_rate": 45,
        "is_legendary": False,
        "is_mythical": False,
        "base_stats": {
            "hp": 45,
            "attack": 49,
            "defense": 49,
            "special_attack": 65,
            "special_defense": 65,
            "speed": 45,
        },
    }

    conn = get_connection()

    insert_species(conn, species)

    conn.commit()
    conn.close()

    print("✔ Bulbasaur insertado en Neon DB")


if __name__ == "__main__":
    main()
