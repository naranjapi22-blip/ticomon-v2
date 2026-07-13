import csv
from dataclasses import replace
from pathlib import Path

import pytest

from core.species import (
    REGIONAL_POKEAPI_IDS,
    is_regional_pokeapi_id,
    is_regional_species,
)
from scripts.import_species import is_regional_row
from test.factories import create_species

CSV_PATH = Path(__file__).parents[3] / "pokemon_data.csv"


def read_species_rows() -> list[dict[str, str]]:
    with CSV_PATH.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def test_regional_catalog_contains_exactly_the_expected_pokeapi_ids():
    assert isinstance(REGIONAL_POKEAPI_IDS, frozenset)
    assert len(REGIONAL_POKEAPI_IDS) == 52
    assert len(set(REGIONAL_POKEAPI_IDS)) == 52
    assert all(pokeapi_id > 0 for pokeapi_id in REGIONAL_POKEAPI_IDS)
    assert {10091, 10100, 10251, 10252} <= REGIONAL_POKEAPI_IDS
    assert 1026 not in REGIONAL_POKEAPI_IDS
    assert 1077 not in REGIONAL_POKEAPI_IDS


def test_regional_pokeapi_lookup_validates_and_classifies_ids():
    assert is_regional_pokeapi_id(10100)
    assert not is_regional_pokeapi_id(25)

    with pytest.raises(ValueError):
        is_regional_pokeapi_id(0)
    with pytest.raises(ValueError):
        is_regional_pokeapi_id(-1)


def test_species_classification_uses_pokeapi_id_not_internal_id():
    first = replace(create_species(id=1), pokeapi_id=10100)
    second = replace(create_species(id=9999), pokeapi_id=10100)
    misleading_internal_id = replace(create_species(id=1026), pokeapi_id=25)

    assert is_regional_species(first)
    assert is_regional_species(second)
    assert not is_regional_species(misleading_internal_id)


def test_importer_selects_the_same_52_csv_rows_by_pokeapi_id():
    rows = read_species_rows()
    selected = [row for row in rows if is_regional_row(row)]

    assert len(selected) == 52
    assert {int(row["pokeapi_id"]) for row in selected} == REGIONAL_POKEAPI_IDS


def test_importer_classification_does_not_depend_on_csv_or_internal_id():
    regional = {
        "id": "999999",
        "pokeapi_id": "10100",
    }
    normal_with_old_range_id = {
        "id": "1026",
        "pokeapi_id": "25",
    }

    assert is_regional_row(regional)
    assert not is_regional_row(normal_with_old_range_id)
