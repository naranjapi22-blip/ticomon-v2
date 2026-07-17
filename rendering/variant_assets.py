from rendering.gif_urls import version_gif_url


def get_variant_asset_key(
    species_name: str,
    variant_name: str,
) -> tuple[str, str]:
    """Maps persisted variant identities to their shared sprite asset key."""
    species = species_name.lower()
    variant = variant_name.lower()

    if species == "oricorio-baile":
        return "oricorio", variant.replace("'", "").replace(chr(0x2019), "")

    return species, variant


def get_variant_gif_url(
    base_url: str,
    species_name: str,
    variant_name: str,
) -> str:
    species, variant = get_variant_asset_key(species_name, variant_name)
    return version_gif_url(
        f"{base_url}/showdown_variantes/{species}/{species}-{variant}.gif"
    )
