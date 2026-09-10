import string
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())

CODE_CHARS = set(string.ascii_uppercase + string.digits)


def _date_ahead(days: int) -> str:
    day = datetime.now(timezone.utc).date() + timedelta(days=days)
    return day.isoformat()


def _passenger(last_name="Петров"):
    return {
        "firstName": "Иван",
        "lastName": last_name,
        "dateOfBirth": "1990-05-20",
        "documentNumber": "1",
    }


def _payload(flight_id, passengers):
    return {
        "flightId": flight_id,
        "contact": {"email": "ivan@example.com", "phone": "+79991234567"},
        "passengers": passengers,
    }


def _a_flight():
    flights = client.get(
        "/api/flights",
        params={"origin": "MOW", "destination": "LED", "date": _date_ahead(3)},
    ).json()
    return flights[0]


def _make_booking(*last_names):
    names = last_names or ("Петров",)
    flight = _a_flight()
    passengers = [_passenger(name) for name in names]
    booking = client.post(
        "/api/bookings", json=_payload(flight["id"], passengers)
    ).json()
    return booking["code"]


def test_health_returns_ok():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_cities_returns_200_and_json_array():
    response = client.get("/api/cities")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 7


def test_cities_order_starts_with_moscow_and_spb():
    body = client.get("/api/cities").json()

    assert [city["code"] for city in body[:2]] == ["MOW", "LED"]
    assert body[0] == {"code": "MOW", "name": "Москва", "country": "Россия"}


def test_unknown_api_path_returns_json_404():
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


def test_flights_search_returns_matching_flights():
    response = client.get(
        "/api/flights",
        params={"origin": "MOW", "destination": "LED", "date": _date_ahead(2)},
    )

    assert response.status_code == 200
    flights = response.json()
    assert len(flights) > 0
    flight = flights[0]
    assert flight["origin"]["code"] == "MOW"
    assert flight["destination"]["code"] == "LED"
    assert flight["departureAt"].endswith("Z")
    assert isinstance(flight["price"]["amount"], int)
    assert flight["price"]["currency"] == "RUB"
    assert set(flight["airline"]) == {"code", "name"}


def test_flights_search_today_returns_flights():
    # Главная ищет рейсы на сегодня — сдвинувшаяся заливка сломала бы её,
    # но прочие тесты берут даты в будущем и этого не заметили бы.
    response = client.get(
        "/api/flights",
        params={"origin": "MOW", "destination": "LED", "date": _date_ahead(0)},
    )

    assert response.status_code == 200
    assert len(response.json()) > 0


def test_flights_search_same_city_returns_empty_list():
    response = client.get(
        "/api/flights",
        params={"origin": "MOW", "destination": "MOW", "date": _date_ahead(2)},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_flights_search_respects_passengers_filter():
    params = {"origin": "MOW", "destination": "LED", "date": _date_ahead(2)}
    all_flights = client.get("/api/flights", params=params).json()
    assert len(all_flights) > 0

    # Порог выше свободных мест любого рейса — не находится ничего.
    max_seats = max(f["seatsAvailable"] for f in all_flights)
    over = client.get(
        "/api/flights", params={**params, "passengers": str(max_seats + 1)}
    ).json()
    assert over == []

    # Порог 2 не превышает мест (их минимум 10) — набор тот же.
    two = client.get(
        "/api/flights", params={**params, "passengers": "2"}
    ).json()
    assert len(two) == len(all_flights)
    assert all(f["seatsAvailable"] >= 2 for f in two)


def test_flights_search_missing_date_returns_400():
    response = client.get(
        "/api/flights", params={"origin": "MOW", "destination": "LED"}
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_flights_search_invalid_passengers_returns_400():
    response = client.get(
        "/api/flights",
        params={
            "origin": "MOW",
            "destination": "LED",
            "date": _date_ahead(2),
            "passengers": "0",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_flight_by_id_returns_flight():
    flights = client.get(
        "/api/flights",
        params={"origin": "MOW", "destination": "LED", "date": _date_ahead(2)},
    ).json()
    flight_id = flights[0]["id"]

    response = client.get(f"/api/flights/{flight_id}")

    assert response.status_code == 200
    assert response.json() == flights[0]


def test_flight_by_unknown_id_returns_404():
    response = client.get("/api/flights/NOPE")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_create_booking_one_passenger():
    flight = _a_flight()
    response = client.post(
        "/api/bookings", json=_payload(flight["id"], [_passenger()])
    )

    assert response.status_code == 201
    booking = response.json()
    assert len(booking["code"]) == 6
    assert set(booking["code"]) <= CODE_CHARS
    assert booking["status"] == "confirmed"
    assert booking["flight"]["id"] == flight["id"]
    assert len(booking["passengers"]) == 1
    assert booking["totalPrice"]["amount"] == flight["price"]["amount"]
    assert booking["totalPrice"]["currency"] == "RUB"
    assert booking["createdAt"].endswith("Z")


def test_create_booking_two_passengers_doubles_total():
    flight = _a_flight()
    passengers = [_passenger("Петров"), _passenger("Сидоров")]
    response = client.post(
        "/api/bookings", json=_payload(flight["id"], passengers)
    )

    assert response.status_code == 201
    booking = response.json()
    assert len(booking["passengers"]) == 2
    assert booking["totalPrice"]["amount"] == flight["price"]["amount"] * 2


def test_create_booking_empty_passengers_returns_400():
    flight = _a_flight()
    response = client.post("/api/bookings", json=_payload(flight["id"], []))

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_create_booking_missing_field_returns_400():
    flight = _a_flight()
    passenger = _passenger()
    del passenger["lastName"]
    response = client.post(
        "/api/bookings", json=_payload(flight["id"], [passenger])
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_create_booking_unknown_flight_returns_400():
    response = client.post(
        "/api/bookings", json=_payload("NOPE", [_passenger()])
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_create_booking_generates_unique_codes():
    flight = _a_flight()
    codes = {
        client.post(
            "/api/bookings", json=_payload(flight["id"], [_passenger()])
        ).json()["code"]
        for _ in range(5)
    }
    assert len(codes) == 5


def test_get_booking_by_code_and_last_name():
    code = _make_booking("Петров")
    response = client.get(
        f"/api/bookings/{code}", params={"lastName": "Петров"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == code
    assert body["status"] == "confirmed"


def test_get_booking_found_by_any_passenger_last_name():
    # Бронь находится по фамилии любого пассажира, не только первого.
    code = _make_booking("Петров", "Сидоров")
    response = client.get(
        f"/api/bookings/{code}", params={"lastName": "Сидоров"}
    )

    assert response.status_code == 200
    assert response.json()["code"] == code


def test_get_booking_last_name_case_and_spaces_insensitive():
    code = _make_booking("Петров")
    response = client.get(
        f"/api/bookings/{code}", params={"lastName": "  пЕтРоВ  "}
    )

    assert response.status_code == 200
    assert response.json()["code"] == code


def test_get_booking_code_is_case_insensitive():
    code = _make_booking("Петров")
    response = client.get(
        f"/api/bookings/{code.lower()}", params={"lastName": "Петров"}
    )

    assert response.status_code == 200
    assert response.json()["code"] == code


def test_get_booking_wrong_last_name_returns_404():
    code = _make_booking("Петров")
    response = client.get(
        f"/api/bookings/{code}", params={"lastName": "Иванов"}
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_get_booking_unknown_code_returns_404():
    response = client.get(
        "/api/bookings/ZZZZZZ", params={"lastName": "Петров"}
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_get_booking_missing_last_name_returns_404():
    code = _make_booking("Петров")
    response = client.get(f"/api/bookings/{code}")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_cancel_booking_returns_cancelled():
    code = _make_booking("Петров")
    response = client.post(
        f"/api/bookings/{code}/cancel", json={"lastName": "Петров"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    # статус сохранился в базе
    persisted = client.get(
        f"/api/bookings/{code}", params={"lastName": "Петров"}
    ).json()
    assert persisted["status"] == "cancelled"


def test_cancel_booking_is_idempotent():
    code = _make_booking("Петров")
    first = client.post(
        f"/api/bookings/{code}/cancel", json={"lastName": "Петров"}
    )
    second = client.post(
        f"/api/bookings/{code}/cancel", json={"lastName": "Петров"}
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "cancelled"


def test_cancel_booking_missing_last_name_returns_404():
    code = _make_booking("Петров")
    response = client.post(f"/api/bookings/{code}/cancel", json={})

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_cancel_booking_wrong_last_name_returns_404():
    code = _make_booking("Петров")
    response = client.post(
        f"/api/bookings/{code}/cancel", json={"lastName": "Иванов"}
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_cancel_booking_non_string_last_name_returns_404():
    # {"lastName": 1} не должен падать 500 — ожидаем обычный 404.
    code = _make_booking("Петров")
    response = client.post(
        f"/api/bookings/{code}/cancel", json={"lastName": 1}
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_head_on_api_returns_json_404_not_index_html():
    for path in ("/api/cities", "/api/does-not-exist"):
        response = client.head(path)
        assert response.status_code == 404, path
        content_type = response.headers["content-type"]
        assert "application/json" in content_type, path
        assert "text/html" not in content_type, path


def test_path_traversal_does_not_leak_files():
    # `..` в пути не должен выдавать файлы за пределами public/.
    response = client.get("/%2e%2e%2f%2e%2e%2fpyproject.toml")

    assert response.status_code == 200
    assert "hexlet-code" not in response.text  # содержимое не утекло
    assert "<!doctype html" in response.text.lower()
