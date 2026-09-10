from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import get_database_url

_pool: ConnectionPool | None = None


def _configure(conn: psycopg.Connection) -> None:
    """Выполняется один раз на создание соединения в пуле.

    Пояс выставляем явно: по умолчанию он берётся с сервера базы, а он на
    локальной машине и на Render разный. В пуле — один SET на соединение,
    а не round-trip на каждый запрос.

    commit обязателен: без него SET оставляет соединение в открытой
    транзакции (INTRANS), и пул такое соединение отбрасывает. Настройка
    пояса — на уровне сессии, коммит её не сбрасывает.
    """
    conn.execute("SET TIME ZONE 'UTC'")
    conn.commit()


def get_pool() -> ConnectionPool:
    """Ленивый пул на процесс. Верхняя граница max_size защищает бесплатную
    базу от исчерпания коннектов при всплеске запросов."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=get_database_url(),
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row},
            configure=_configure,
            open=True,
        )
    return _pool


def get_db() -> Iterator[psycopg.Connection]:
    """FastAPI-зависимость: соединение из пула на время запроса.

    Явные getconn/putconn с finally: соединение обязательно возвращается
    в пул после запроса, включая путь с исключением.
    """
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """Отдельное соединение для разовых задач (миграции, заливка данных),
    которые не проходят через пул запросов."""
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
