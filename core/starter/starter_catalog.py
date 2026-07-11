STARTER_REGIONS = {
    "Kanto": (
        1,  # Bulbasaur
        4,  # Charmander
        7,  # Squirtle
    ),
    "Johto": (
        152,  # Chikorita
        155,  # Cyndaquil
        158,  # Totodile
    ),
    "Hoenn": (
        252,  # Treecko
        255,  # Torchic
        258,  # Mudkip
    ),
    "Sinnoh": (
        387,  # Turtwig
        390,  # Chimchar
        393,  # Piplup
    ),
    "Unova": (
        495,  # Snivy
        498,  # Tepig
        501,  # Oshawott
    ),
    "Kalos": (
        650,  # Chespin
        653,  # Fennekin
        656,  # Froakie
    ),
    "Alola": (
        722,  # Rowlet
        725,  # Litten
        728,  # Popplio
    ),
    "Galar": (
        810,  # Grookey
        813,  # Scorbunny
        816,  # Sobble
    ),
    "Paldea": (
        906,  # Sprigatito
        909,  # Fuecoco
        912,  # Quaxly
    ),
}
STARTER_SPECIES = {
    species_id for starters in STARTER_REGIONS.values() for species_id in starters
}


def is_starter(
    species_id: int,
) -> bool:
    return species_id in STARTER_SPECIES
