BASE_GIF_URL = "https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev"


def version_gif_url(url: str) -> str:
    """Return the GIF URL without cache-version query parameters."""
    return url.split("?", maxsplit=1)[0]
