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
    """Проверяем присутствие и непустоту обязательных полей (не форматы).
    documentNumber "1" обязан проходить. Возвращает (данные, ошибка)."""
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
    """Создаёт бронь и её пассажиров одной транзакцией.
    Стоимость считает сервер: цена рейса × число пассажиров."""
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


__all__ = ["create_booking", "generate_code", "get_flight"]
