from core.species.species_mapper import SpeciesMapper
from infrastructure.db_config import get_connection


class SpeciesRepository:

    @staticmethod
    def get_all():
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM species;")
        rows = cur.fetchall()

        species_list = [SpeciesMapper.from_row(row) for row in rows]

        cur.close()
        conn.close()

        return species_list

    @staticmethod
    def get_by_name(name: str):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM species WHERE name = %s;", (name,))
        row = cur.fetchone()

        cur.close()
        conn.close()

        if not row:
            return None

        return SpeciesMapper.from_row(row)