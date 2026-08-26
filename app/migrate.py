from pathlib import Path

from yoyo import get_backend, read_migrations

from app.config import get_database_url

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def _yoyo_url(url: str) -> str:
    """yoyo выбирает драйвер по схеме URL. Нам нужен psycopg 3 —
    его backend зарегистрирован на схему postgresql+psycopg."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def apply_migrations() -> None:
    backend = get_backend(_yoyo_url(get_database_url()))
    migrations = read_migrations(str(MIGRATIONS_DIR))
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))


if __name__ == "__main__":
    apply_migrations()
