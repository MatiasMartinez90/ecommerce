from pathlib import Path

import pytest

from ecommerce_api.migrate import migration_up


def test_migration_up_returns_only_forward_sql(tmp_path: Path) -> None:
    path = tmp_path / "001.sql"
    path.write_text("-- migrate:up\nSELECT 1;\n-- migrate:down\nSELECT 2;", encoding="utf-8")
    assert migration_up(path) == "SELECT 1;"


def test_migration_requires_both_markers(tmp_path: Path) -> None:
    path = tmp_path / "broken.sql"
    path.write_text("SELECT 1;", encoding="utf-8")
    with pytest.raises(ValueError):
        migration_up(path)
