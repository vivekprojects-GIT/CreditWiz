from urllib.parse import urlsplit


def safe_link(value: str) -> str:
    if not value:
        return value
    if any(ord(c) < 32 for c in value) or "\\" in value:
        raise ValueError("Invalid link")
    parsed = urlsplit(value)
    if value.startswith("/") and not value.startswith("//"):
        return value
    if parsed.scheme in ("https", "http") and parsed.hostname:
        return value
    raise ValueError("Links must be HTTP(S) URLs or root-relative hub paths")
