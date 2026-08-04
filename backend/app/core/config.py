from functools import lru_cache
from os import getenv


@lru_cache
def get_database_url() -> str:
    database_url = getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required")
    return database_url
