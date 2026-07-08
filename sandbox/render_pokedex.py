import asyncio

from application.bootstrap.core import build_core
from rendering.pokedex.renderer import PokedexRenderer

TRAINER_ID = 113100351531417600


async def main():

    core = build_core()

    pokedex = await core.pokedex_service.get_pokedex(
        trainer_id=TRAINER_ID,
    )

    renderer = PokedexRenderer()

    image = renderer.render(
        pokedex.entries,
        page=1,
    )

    image.save("sandbox/pokedex_test.png")

    print("Pokédex renderizada.")


if __name__ == "__main__":
    asyncio.run(main())
