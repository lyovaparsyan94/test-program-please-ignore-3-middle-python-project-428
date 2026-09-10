import psycopg


def serialize(row: dict) -> dict:
    return {"code": row["code"], "name": row["name"], "country": row["country"]}


def list_cities(conn: psycopg.Connection) -> list[dict]:
    # ORDER BY position: фронтенд берёт первые два города для поиска на главной.
    rows = conn.execute(
        "SELECT code, name, country FROM cities ORDER BY position"
    ).fetchall()
    return [serialize(row) for row in rows]
