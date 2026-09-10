import hashlib
from datetime import datetime, timedelta, timezone

from app.db import get_connection

# Порядок важен: фронтенд берёт первый и второй город для поиска на главной.
CITIES = [
    ("MOW", "Москва", "Россия"),
    ("LED", "Санкт-Петербург", "Россия"),
    ("AER", "Сочи", "Россия"),
    ("KZN", "Казань", "Россия"),
    ("SVX", "Екатеринбург", "Россия"),
    ("OVB", "Новосибирск", "Россия"),
    ("KGD", "Калининград", "Россия"),
]

AIRLINES = [
    ("SU", "Аэрофлот"),
    ("DP", "Победа"),
    ("S7", "S7 Airlines"),
    ("U6", "Уральские авиалинии"),
]

DAYS_AHEAD = 30
CURRENCY = "RUB"


def _seed(*parts: object) -> int:
    """Детерминированное псевдослучайное число из ключа: одинаковый
    ключ — одинаковый результат, отладка предсказуема."""
    key = "|".join(str(p) for p in parts)
    return int(hashlib.sha256(key.encode()).hexdigest(), 16)


def _build_flights(today):
    codes = [code for code, _, _ in CITIES]
    airline_codes = [code for code, _ in AIRLINES]
    rows = []
    for origin in codes:
        for destination in codes:
            if origin == destination:
                continue
            for day in range(DAYS_AHEAD):
                flight_date = today + timedelta(days=day)
                # Ключ — абсолютная дата, как и у остальных атрибутов ниже:
                # иначе одна и та же дата на разных запусках дала бы разное
                # число рейсов, и предсказуемость из докстринга не держалась бы.
                count = 2 + _seed(origin, destination, flight_date.isoformat(), "count") % 2
                for idx in range(count):
                    h = _seed(origin, destination, flight_date.isoformat(), idx)
                    airline = airline_codes[h % len(airline_codes)]
                    number = 1000 + (h // 4) % 9000
                    duration = 80 + (h // 7) % (280 - 80 + 1)
                    price = 3000 + (h // 11) % (8500 - 3000 + 1)
                    seats = 10 + (h // 13) % (90 - 10 + 1)
                    dep_hour = (h // 17) % 24
                    dep_minute = ((h // 19) % 12) * 5
                    departure_at = datetime(
                        flight_date.year, flight_date.month, flight_date.day,
                        dep_hour, dep_minute, tzinfo=timezone.utc,
                    )
                    arrival_at = departure_at + timedelta(minutes=duration)
                    flight_id = f"fl-{origin}-{destination}-{flight_date:%Y%m%d}-{idx}"
                    rows.append((
                        flight_id, f"{airline}{number}", airline,
                        origin, destination, departure_at, arrival_at,
                        duration, price, CURRENCY, seats,
                    ))
    return rows


def seed() -> None:
    today = datetime.now(timezone.utc).date()
    flights = _build_flights(today)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Справочники — обновляемы: чинятся при повторном запуске.
            cur.executemany(
                """
                INSERT INTO cities (code, name, country, position)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (code) DO UPDATE
                SET name = EXCLUDED.name,
                    country = EXCLUDED.country,
                    position = EXCLUDED.position
                """,
                [(c, n, country, i) for i, (c, n, country) in enumerate(CITIES)],
            )
            cur.executemany(
                """
                INSERT INTO airlines (code, name)
                VALUES (%s, %s)
                ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
                """,
                AIRLINES,
            )
            # Рейсы — DO NOTHING: детерминированный id уже задаёт все атрибуты,
            # так что повторная заливка не плодит дубли и не трогает существующие
            # строки (id — первичный ключ, конфликт просто пропускается).
            cur.executemany(
                """
                INSERT INTO flights (
                    id, flight_number, airline_code, origin_code,
                    destination_code, departure_at, arrival_at,
                    duration_minutes, price_amount, currency, seats_available
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                flights,
            )


if __name__ == "__main__":
    seed()
