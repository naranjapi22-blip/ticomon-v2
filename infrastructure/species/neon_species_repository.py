from core.rarity import Rarity
from core.species.species import Species
from core.species.species_mapper import SpeciesMapper
from core.species.species_repository import SpeciesRepository
from core.species.variant import Variant
from infrastructure.db_config import get_pool
from infrastructure.species.evolution_chain_loader import build_evolution_chains


class NeonSpeciesRepository(SpeciesRepository):
    """
    PostgreSQL implementation of SpeciesRepository backed by Neon.
    """

    def __init__(self) -> None:
        self._mapper = SpeciesMapper()

    async def _load_variants(
        self,
        connection,
        species_id: int,
    ) -> tuple[Variant, ...]:
        rows = await connection.fetch(
            """
            SELECT id, name
            FROM species_variants
            WHERE species_id = $1
            ORDER BY id
            """,
            species_id,
        )

        return tuple(
            Variant(
                id=row["id"],
                name=row["name"],
            )
            for row in rows
        )

    async def _load_all_variants(
        self,
        connection,
    ) -> dict[int, tuple[Variant, ...]]:

        rows = await connection.fetch("""
            SELECT
                species_id,
                id,
                name
            FROM species_variants
            ORDER BY species_id, id
            """)

        variants: dict[int, list[Variant]] = {}

        for row in rows:

            variants.setdefault(
                row["species_id"],
                [],
            ).append(
                Variant(
                    id=row["id"],
                    name=row["name"],
                )
            )

        return {species_id: tuple(values) for species_id, values in variants.items()}

    async def _load_variants_for_species(
        self,
        connection,
        species_ids: list[int],
    ) -> dict[int, tuple[Variant, ...]]:
        if not species_ids:
            return {}

        rows = await connection.fetch(
            """
            SELECT species_id, id, name
            FROM species_variants
            WHERE species_id = ANY($1::bigint[])
            ORDER BY species_id, id
            """,
            species_ids,
        )
        variants: dict[int, list[Variant]] = {}

        for row in rows:
            variants.setdefault(row["species_id"], []).append(
                Variant(id=row["id"], name=row["name"])
            )

        return {species_id: tuple(values) for species_id, values in variants.items()}

    @staticmethod
    async def _load_evolution_chains(connection):
        rows = await connection.fetch(
            "SELECT from_species_id, to_species_id, tier FROM pokemon_evolutions"
        )
        return build_evolution_chains(rows)

    async def get(
        self,
        species_id: int,
    ) -> Species:
        """
        Returns a species by its identifier.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            row = await connection.fetchrow(
                """
                SELECT *
                FROM species
                WHERE id = $1
                """,
                species_id,
            )

            if row is None:
                raise ValueError(f"Species with id {species_id} was not found.")

            variants = await self._load_variants(
                connection,
                species_id,
            )
            chains = await self._load_evolution_chains(connection)

        return self._mapper.from_row(
            row,
            variants,
            chains.get(species_id),
        )

    async def find_by_name(
        self,
        name: str,
    ) -> Species | None:
        """
        Returns a species by its name.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            row = await connection.fetchrow(
                """
                SELECT *
                FROM species
                WHERE name ILIKE $1
                """,
                name,
            )

            if row is None:
                return None

            variants = await self._load_variants(
                connection,
                row["id"],
            )
            chains = await self._load_evolution_chains(connection)

        return self._mapper.from_row(
            row,
            variants,
            chains.get(row["id"]),
        )

    async def find_many_by_names(
        self,
        names: list[str] | tuple[str, ...],
    ) -> dict[str, Species]:
        canonical_names = list(dict.fromkeys(names))
        if not canonical_names:
            return {}

        pool = await get_pool()

        async with pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT *
                FROM species
                WHERE name = ANY($1::text[])
                ORDER BY id
                """,
                canonical_names,
            )
            variants_by_species = await self._load_variants_for_species(
                connection,
                [row["id"] for row in rows],
            )
            chains = await self._load_evolution_chains(connection)

        return {
            row["name"]: self._mapper.from_row(
                row,
                variants_by_species.get(row["id"], ()),
                chains.get(row["id"]),
            )
            for row in rows
        }

    async def get_all(
        self,
    ) -> tuple[Species, ...]:
        """
        Returns all registered species ordered by identifier.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            rows = await connection.fetch("""
                SELECT *
                FROM species
                ORDER BY id
                """)

            variants_map = await self._load_all_variants(
                connection,
            )
            chains = await self._load_evolution_chains(connection)

            species = []

            for row in rows:

                species.append(
                    self._mapper.from_row(
                        row,
                        variants_map.get(
                            row["id"],
                            (),
                        ),
                        chains.get(row["id"]),
                    )
                )

        return tuple(species)

    async def find_by_spawn_rarity(
        self,
        rarity: Rarity,
    ) -> tuple[Species, ...]:
        """
        Returns all species belonging to the given spawn rarity.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            rows = await connection.fetch(
                """
                SELECT *
                FROM species
                WHERE spawn_rarity = $1
                ORDER BY id
                """,
                rarity.value,
            )

            variants_map = await self._load_variants_for_species(
                connection,
                [row["id"] for row in rows],
            )
            chains = await self._load_evolution_chains(connection)

            species = []

            for row in rows:

                species.append(
                    self._mapper.from_row(
                        row,
                        variants_map.get(
                            row["id"],
                            (),
                        ),
                        chains.get(row["id"]),
                    )
                )

        return tuple(species)

    async def get_many(
        self,
        species_ids: list[int] | tuple[int, ...],
    ) -> list[Species]:
        """
        Returns all species matching the given identifiers.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            rows = await connection.fetch(
                """
                SELECT *
                FROM species
                WHERE id = ANY($1::int[])
                ORDER BY id
                """,
                list(species_ids),
            )

            variants_map = await self._load_variants_for_species(
                connection,
                [row["id"] for row in rows],
            )
            chains = await self._load_evolution_chains(connection)

            species = []

            for row in rows:

                species.append(
                    self._mapper.from_row(
                        row,
                        variants_map.get(
                            row["id"],
                            (),
                        ),
                        chains.get(row["id"]),
                    )
                )

        return species
