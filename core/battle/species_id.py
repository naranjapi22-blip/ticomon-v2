import re


def to_species_showdown_id(species_name: str) -> str:
    normalized = species_name.lower().strip()
    normalized = normalized.replace("'", "").replace(".", "")
    normalized = re.sub(r"[^a-z0-9]+", "", normalized)
    return normalized
