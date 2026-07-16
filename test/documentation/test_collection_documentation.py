from pathlib import Path

from core.collection.catalog import COLLECTIONS

ROOT = Path(__file__).resolve().parents[2]


def test_collection_documentation_matches_the_supported_catalogue():
    document = (ROOT / "docs" / "collections.md").read_text(encoding="utf-8")
    assert "!collections" in document
    assert "45 canonical decorated combinations" in document
    assert "17 verified normal patterns" in document
    assert "Rotom\nFrost and Rotom Fan remain excluded" in document
    assert "Eternal Floette" in document
    assert len(COLLECTIONS) == 6


def test_readme_marks_collections_as_implemented():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Thematic Collections" in readme
    assert "✅ Thematic collections" in readme
