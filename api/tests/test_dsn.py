from ecommerce_api.dsn import sanitize_database_url


def test_sanitize_removes_pgbouncer_parameter() -> None:
    value = sanitize_database_url(
        "postgresql://user:pass@db:5432/shop?prepared_statements=false&sslmode=disable"
    )
    assert value == "postgresql://user:pass@db:5432/shop?sslmode=disable"
