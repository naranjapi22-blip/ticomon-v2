STARTER_SPECIES = (
    1,  # Bulbasaur
    4,  # Charmander
    7,  # Squirtle
    152,  # Chikorita
    155,  # Cyndaquil
    158,  # Totodile
    252,  # Treecko
    255,  # Torchic
    258,  # Mudkip
    387,  # Turtwig
    390,  # Chimchar
    393,  # Piplup
    495,  # Snivy
    498,  # Tepig
    501,  # Oshawott
    650,  # Chespin
    653,  # Fennekin
    656,  # Froakie
    722,  # Rowlet
    725,  # Litten
    728,  # Popplio
    810,  # Grookey
    813,  # Scorbunny
    816,  # Sobble
    906,  # Sprigatito
    909,  # Fuecoco
    912,  # Quaxly
)


def is_starter(species_id: int) -> bool:
    return species_id in STARTER_SPECIES
