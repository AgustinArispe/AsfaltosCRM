import pytest

from app.core.config import clear_runtime_settings_caches, get_database_url


@pytest.mark.parametrize(
    ("database_url", "expected_url"),
    [
        (
            "postgresql://faa:password@db.example/crm",
            "postgresql+psycopg://faa:password@db.example/crm",
        ),
        (
            "postgresql+psycopg://faa:password@db.example/crm",
            "postgresql+psycopg://faa:password@db.example/crm",
        ),
        (
            "postgresql+asyncpg://faa:password@db.example/crm",
            "postgresql+asyncpg://faa:password@db.example/crm",
        ),
    ],
)
def test_get_database_url_normalizes_plain_urls_and_preserves_explicit_drivers(
    monkeypatch: pytest.MonkeyPatch,
    database_url: str,
    expected_url: str,
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    clear_runtime_settings_caches()

    try:
        assert get_database_url() == expected_url
    finally:
        clear_runtime_settings_caches()
