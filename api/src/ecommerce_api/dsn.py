from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def sanitize_database_url(value: str) -> str:
    """Remove libpq-only PgBouncer flags that asyncpg rejects as startup params."""
    parts = urlsplit(value)
    query = [(key, item) for key, item in parse_qsl(parts.query, keep_blank_values=True)
             if key != "prepared_statements"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
