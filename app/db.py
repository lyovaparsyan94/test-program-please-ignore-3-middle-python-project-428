from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from app.config import get_database_url


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """Соединение с БД: строки — как dict, часовой пояс сессии — UTC.

    Пояс выставляем явно: по умолчанию он берётся с сервера базы,
    а он на локальной машине и на Render разный.
    """
    conn = psycopg.connect(get_database_url(), row_factory=dict_row)
    try:
        conn.execute("SET TIME ZONE 'UTC'")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_db() -> Iterator[psycopg.Connection]:
    """FastAPI-зависимость: соединение на время запроса."""
    with get_connection() as conn:
        yield conn
