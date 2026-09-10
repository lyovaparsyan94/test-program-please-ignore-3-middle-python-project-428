import psycopg


def serialize(row: dict) -> dict:
    # Явное отображение колонок в поля контракта: переименование в схеме
    # ловится здесь, а не «протекает» в JSON, который видит фронтенд.
    return {
        "code": row["code"],
        "name": row["name"],
        "country": row["country"],
    }


def list_cities(conn: psycopg.Connection) -> list[dict]:
    # Порядок важен: фронтенд берёт первые два города для поиска на главной.
    rows = conn.execute(
        "SELECT code, name, country FROM cities ORDER BY position"
    ).fetchall()
    return [serialize(row) for row in rows]
