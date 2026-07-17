from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

BASE_GIF_URL = "https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev"
GIF_ASSET_VERSION = "20260717-1"


def version_gif_url(url: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["v"] = GIF_ASSET_VERSION
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        )
    )
