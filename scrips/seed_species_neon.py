import psycopg2


def insert_species(conn: psycopg2.extensions.connection, species: dict) -> None:
    cur = conn.cursor()

    types = species["types"]
    type_1 = types[0] if len(types) > 0 else None
    type_2 = types[1] if len(types) > 1 else None

    stats = species["base_stats"]

    cur.execute(
        """
        INSERT INTO species (
            pokeapi_id,
            name,
            type_1,
            type_2,
            height,
            weight,
            display_scale,
            capture_rate,
            generation,
            is_baby,
            is_legendary,
            is_mythical,
            hp,
            attack,
            defense,
            special_attack,
            special_defense,
            speed
        )
        VALUES (
            %s, %s,
            %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s
        )
        ON CONFLICT (pokeapi_id)
        DO UPDATE SET
            name = EXCLUDED.name,
            type_1 = EXCLUDED.type_1,
            type_2 = EXCLUDED.type_2,
            height = EXCLUDED.height,
            weight = EXCLUDED.weight,
            display_scale = EXCLUDED.display_scale,
            capture_rate = EXCLUDED.capture_rate,
            generation = EXCLUDED.generation,
            is_baby = EXCLUDED.is_baby,
            is_legendary = EXCLUDED.is_legendary,
            is_mythical = EXCLUDED.is_mythical,
            hp = EXCLUDED.hp,
            attack = EXCLUDED.attack,
            defense = EXCLUDED.defense,
            special_attack = EXCLUDED.special_attack,
            special_defense = EXCLUDED.special_defense,
            speed = EXCLUDED.speed;
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
            species["generation"],
            species["is_baby"],
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
