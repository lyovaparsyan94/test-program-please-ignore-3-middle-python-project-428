import secrets
from datetime import date

import psycopg

from app.flights import _iso_z, get_flight

# Без 0, O, 1, I — код можно диктовать вслух, как в реальных системах.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6
CURRENCY = "RUB"
_MAX_CODE_ATTEMPTS = 10


def generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


_PASSENGER_FIELDS = ("firstName", "lastName", "dateOfBirth", "documentNumber")


def _non_empty_str(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def validate_payload(body: object) -> tuple[dict | None, str | None]:
    # Только присутствие и непустота полей, не форматы: documentNumber "1" проходит.
    if not isinstance(body, dict):
        return None, "Тело запроса должно быть объектом"

    if not _non_empty_str(body.get("flightId")):
        return None, "flightId обязателен"

    contact = body.get("contact")
    if not isinstance(contact, dict) or not _non_empty_str(contact.get("email")) \
            or not _non_empty_str(contact.get("phone")):
        return None, "contact.email и contact.phone обязательны"

    passengers = body.get("passengers")
    if not isinstance(passengers, list) or len(passengers) == 0:
        return None, "passengers не может быть пустым"

    parsed_passengers = []
    for passenger in passengers:
        if not isinstance(passenger, dict):
            return None, "Некорректные данные пассажира"
        for field in _PASSENGER_FIELDS:
            if not _non_empty_str(passenger.get(field)):
                return None, f"Поле пассажира {field} обязательно"
        try:
            dob = date.fromisoformat(passenger["dateOfBirth"])
        except ValueError:
            return None, "dateOfBirth должен быть в формате YYYY-MM-DD"
        parsed_passengers.append({
            "firstName": passenger["firstName"],
            "lastName": passenger["lastName"],
            "dateOfBirth": dob,
            "documentNumber": passenger["documentNumber"],
        })

    return {
        "flightId": body["flightId"],
        "contact": {"email": contact["email"], "phone": contact["phone"]},
        "passengers": parsed_passengers,
    }, None


def _serialize_passenger(passenger: dict) -> dict:
    dob = passenger["dateOfBirth"]
    return {
        "firstName": passenger["firstName"],
        "lastName": passenger["lastName"],
        "dateOfBirth": dob.isoformat() if isinstance(dob, date) else dob,
        "documentNumber": passenger["documentNumber"],
    }


def create_booking(
    conn: psycopg.Connection,
    flight: dict,
    contact: dict,
    passengers: list[dict],
) -> dict:
    # Бронь и пассажиры — одной транзакцией; сумму считает сервер.
    total = flight["price"]["amount"] * len(passengers)

    # Уникальность кода держит ограничение в БД; при коллизии — ретрай.
    for _ in range(_MAX_CODE_ATTEMPTS):
        code = generate_code()
        try:
            with conn.transaction():
                row = conn.execute(
                    """
                    INSERT INTO bookings (
                        code, status, flight_id, contact_email,
                        contact_phone, total_price_amount, currency
                    )
                    VALUES (%s, 'confirmed', %s, %s, %s, %s, %s)
                    RETURNING id, created_at
                    """,
                    (code, flight["id"], contact["email"], contact["phone"],
                     total, CURRENCY),
                ).fetchone()
                conn.cursor().executemany(
                    """
                    INSERT INTO passengers (
                        booking_id, first_name, last_name,
                        date_of_birth, document_number
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [(row["id"], p["firstName"], p["lastName"],
                      p["dateOfBirth"], p["documentNumber"]) for p in passengers],
                )
            break
        except psycopg.errors.UniqueViolation:
            continue
    else:
        raise RuntimeError("Не удалось сгенерировать уникальный код брони")

    return {
        "code": code,
        "status": "confirmed",
        "flight": flight,
        "passengers": [_serialize_passenger(p) for p in passengers],
        "contact": {"email": contact["email"], "phone": contact["phone"]},
        "totalPrice": {"amount": total, "currency": CURRENCY},
        "createdAt": _iso_z(row["created_at"]),
    }


_BOOKING_COLUMNS = """
    id, code, status, flight_id, contact_email, contact_phone,
    total_price_amount, currency, created_at
"""


def _serialize_booking(conn: psycopg.Connection, booking: dict) -> dict:
    flight = get_flight(conn, booking["flight_id"])
    passengers = conn.execute(
        """
        SELECT first_name, last_name, date_of_birth, document_number
        FROM passengers WHERE booking_id = %s ORDER BY id
        """,
        (booking["id"],),
    ).fetchall()
    return {
        "code": booking["code"],
        "status": booking["status"],
        "flight": flight,
        "passengers": [{
            "firstName": p["first_name"],
            "lastName": p["last_name"],
            "dateOfBirth": p["date_of_birth"].isoformat(),
            "documentNumber": p["document_number"],
        } for p in passengers],
        "contact": {
            "email": booking["contact_email"],
            "phone": booking["contact_phone"],
        },
        "totalPrice": {
            "amount": booking["total_price_amount"],
            "currency": booking["currency"],
        },
        "createdAt": _iso_z(booking["created_at"]),
    }


def _find_booking(conn: psycopg.Connection, code: str, last_name: str | None) -> dict | None:
    # Любая неудача (нет кода / не та фамилия / нет фамилии) — один и тот же None,
    # чтобы перебором нельзя было отличить существующий код от несуществующего.
    # _non_empty_str, а не .strip(): для {"lastName": 1} .strip() дал бы 500.
    if not _non_empty_str(last_name):
        return None

    # Код из адреса нормализуем к виду, в котором храним.
    booking = conn.execute(
        f"SELECT {_BOOKING_COLUMNS} FROM bookings WHERE code = %s",
        (code.strip().upper(),),
    ).fetchone()
    if booking is None:
        return None

    # Фамилию сверяем в БД: без регистра, по индексу lower(last_name).
    match = conn.execute(
        "SELECT 1 FROM passengers WHERE booking_id = %s AND lower(last_name) = lower(%s) LIMIT 1",
        (booking["id"], last_name.strip()),
    ).fetchone()
    return booking if match is not None else None


def get_booking(conn: psycopg.Connection, code: str, last_name: str | None) -> dict | None:
    booking = _find_booking(conn, code, last_name)
    return _serialize_booking(conn, booking) if booking else None


def cancel_booking(conn: psycopg.Connection, code: str, last_name: str | None) -> dict | None:
    booking = _find_booking(conn, code, last_name)
    if booking is None:
        return None
    # Повторная отмена допустима — просто снова вернём cancelled.
    if booking["status"] != "cancelled":
        conn.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE id = %s",
            (booking["id"],),
        )
        booking["status"] = "cancelled"
    return _serialize_booking(conn, booking)
