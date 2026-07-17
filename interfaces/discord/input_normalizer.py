import re


def normalize_text(value: str) -> str:
    return value.strip().casefold()


def parse_collection_number(value: str) -> int:
    normalized = value.strip()

    if not normalized:
        raise ValueError("No collection number was provided.")

    if re.search(r"[,\s]", normalized):
        raise ValueError("Collection number must be singular.")

    return int(normalized)
