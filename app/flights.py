from datetime import date, datetime, timezone

import psycopg

# Города и авиакомпания — целиком, поэтому джойним справочники одним запросом.
_SELECT = """
    SELECT
        f.id,
        f.flight_number,
        f.departure_at,
        f.arrival_at,
        f.duration_minutes,
        f.price_amount,
        f.currency,
        f.seats_available,
        al.code AS airline_code,
        al.name AS airline_name,
        o.code AS origin_code,
        o.name AS origin_name,
        o.country AS origin_country,
        d.code AS destination_code,
        d.name AS destination_name,
        d.country AS destination_country
    FROM flights f
    JOIN airlines al ON al.code = f.airline_code
    JOIN cities o ON o.code = f.origin_code
    JOIN cities d ON d.code = f.destination_code
"""


def _iso_z(value: datetime) -> str:
    # С Z на конце: фронтенд разбирает Z, а Python по умолчанию даёт +00:00.
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def serialize(row: dict) -> dict:
    return {
        "id": row["id"],
        "flightNumber": row["flight_number"],
        "airline": {"code": row["airline_code"], "name": row["airline_name"]},
        "origin": {
            "code": row["origin_code"],
            "name": row["origin_name"],
            "country": row["origin_country"],
        },
        "destination": {
            "code": row["destination_code"],
            "name": row["destination_name"],
            "country": row["destination_country"],
        },
        "departureAt": _iso_z(row["departure_at"]),
        "arrivalAt": _iso_z(row["arrival_at"]),
        "durationMinutes": row["duration_minutes"],
        "price": {"amount": row["price_amount"], "currency": row["currency"]},
        "seatsAvailable": row["seats_available"],
    }


def search_flights(
    conn: psycopg.Connection,
    origin: str,
    destination: str,
    departure_date: date,
    passengers: int,
) -> list[dict]:
    # День сравниваем в UTC — как отдаём departureAt, иначе утренние рейсы уедут в соседний день.
    rows = conn.execute(
        _SELECT
        + """
        WHERE f.origin_code = %(origin)s
          AND f.destination_code = %(destination)s
          AND (f.departure_at AT TIME ZONE 'UTC')::date = %(date)s
          AND f.seats_available >= %(passengers)s
        ORDER BY f.departure_at
        """,
        {
            "origin": origin,
            "destination": destination,
            "date": departure_date,
            "passengers": passengers,
        },
    ).fetchall()
    return [serialize(row) for row in rows]


def get_flight(conn: psycopg.Connection, flight_id: str) -> dict | None:
    row = conn.execute(
        _SELECT + " WHERE f.id = %(id)s", {"id": flight_id}
    ).fetchone()
    return serialize(row) if row else None
