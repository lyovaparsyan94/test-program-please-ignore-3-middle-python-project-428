import os

# Локальный дефолт совпадает с docker-контейнером flights-db.
DEFAULT_DATABASE_URL = "postgresql://flights:flights@localhost:5432/flights"


def get_database_url() -> str:
    """DSN для приложения (psycopg). Берётся из DATABASE_URL."""
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_port() -> int:
    return int(os.environ.get("PORT", "8080"))
