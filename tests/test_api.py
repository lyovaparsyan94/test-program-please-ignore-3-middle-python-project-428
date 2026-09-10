from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def _date_ahead(days: int) -> str:
    return (datetime.now(timezone.utc).date() + timedelta(days=days)).isoformat()


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
    date = _date_ahead(2)
    response = client.get(
        "/api/flights",
        params={"origin": "MOW", "destination": "LED", "date": date},
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


def test_flights_search_same_city_returns_empty_list():
    response = client.get(
        "/api/flights",
        params={"origin": "MOW", "destination": "MOW", "date": _date_ahead(2)},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_flights_search_respects_passengers_filter():
    date = _date_ahead(2)
    params = {"origin": "MOW", "destination": "LED", "date": date}
    all_flights = client.get("/api/flights", params=params).json()

    huge = client.get("/api/flights", params={**params, "passengers": "999"}).json()
    assert huge == []

    assert all(f["seatsAvailable"] >= 2
               for f in client.get("/api/flights", params={**params, "passengers": "2"}).json())
    assert len(all_flights) >= len(huge)


def test_flights_search_missing_date_returns_400():
    response = client.get(
        "/api/flights", params={"origin": "MOW", "destination": "LED"}
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_flights_search_invalid_passengers_returns_400():
    response = client.get(
        "/api/flights",
        params={"origin": "MOW", "destination": "LED",
                "date": _date_ahead(2), "passengers": "0"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_flight_by_id_returns_flight():
    date = _date_ahead(2)
    flights = client.get(
        "/api/flights",
        params={"origin": "MOW", "destination": "LED", "date": date},
    ).json()
    flight_id = flights[0]["id"]

    response = client.get(f"/api/flights/{flight_id}")

    assert response.status_code == 200
    assert response.json() == flights[0]


def test_flight_by_unknown_id_returns_404():
    response = client.get("/api/flights/NOPE")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def _a_flight():
    flights = client.get(
        "/api/flights",
        params={"origin": "MOW", "destination": "LED", "date": _date_ahead(3)},
    ).json()
    return flights[0]


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


def test_create_booking_one_passenger():
    flight = _a_flight()
    response = client.post("/api/bookings", json=_payload(flight["id"], [_passenger()]))

    assert response.status_code == 201
    booking = response.json()
    assert len(booking["code"]) == 6
    assert all(ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for ch in booking["code"])
    assert booking["status"] == "confirmed"
    assert booking["flight"]["id"] == flight["id"]
    assert len(booking["passengers"]) == 1
    assert booking["totalPrice"]["amount"] == flight["price"]["amount"]
    assert booking["totalPrice"]["currency"] == "RUB"
    assert booking["createdAt"].endswith("Z")


def test_create_booking_two_passengers_doubles_total():
    flight = _a_flight()
    payload = _payload(flight["id"], [_passenger("Петров"), _passenger("Сидоров")])
    response = client.post("/api/bookings", json=payload)

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
    response = client.post("/api/bookings", json=_payload(flight["id"], [passenger]))

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_create_booking_unknown_flight_returns_400():
    response = client.post("/api/bookings", json=_payload("NOPE", [_passenger()]))

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_create_booking_generates_unique_codes():
    flight = _a_flight()
    codes = {
        client.post("/api/bookings", json=_payload(flight["id"], [_passenger()]))
        .json()["code"]
        for _ in range(5)
    }
    assert len(codes) == 5


def _make_booking(last_name="Петров"):
    flight = _a_flight()
    booking = client.post(
        "/api/bookings", json=_payload(flight["id"], [_passenger(last_name)])
    ).json()
    return booking["code"]


def test_get_booking_by_code_and_last_name():
    code = _make_booking("Петров")
    response = client.get(f"/api/bookings/{code}", params={"lastName": "Петров"})

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == code
    assert body["status"] == "confirmed"


def test_get_booking_last_name_case_and_spaces_insensitive():
    code = _make_booking("Петров")
    response = client.get(f"/api/bookings/{code}", params={"lastName": "  пЕтРоВ  "})

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
    response = client.get(f"/api/bookings/{code}", params={"lastName": "Иванов"})

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_get_booking_unknown_code_returns_404():
    response = client.get("/api/bookings/ZZZZZZ", params={"lastName": "Петров"})

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
    assert client.get(
        f"/api/bookings/{code}", params={"lastName": "Петров"}
    ).json()["status"] == "cancelled"


def test_cancel_booking_is_idempotent():
    code = _make_booking("Петров")
    first = client.post(f"/api/bookings/{code}/cancel", json={"lastName": "Петров"})
    second = client.post(f"/api/bookings/{code}/cancel", json={"lastName": "Петров"})

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
    response = client.post(f"/api/bookings/{code}/cancel", json={"lastName": 1})

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_head_on_api_returns_json_404_not_index_html():
    for path in ("/api/cities", "/api/does-not-exist"):
        response = client.head(path)
        assert response.status_code == 404, path
        assert "application/json" in response.headers["content-type"], path
        assert "text/html" not in response.headers["content-type"], path


def test_path_traversal_does_not_leak_files():
    # `..` в пути не должен выдавать файлы за пределами public/.
    response = client.get("/%2e%2e%2f%2e%2e%2fpyproject.toml")

    assert response.status_code == 200
    assert "hexlet-code" not in response.text  # содержимое pyproject не утекло
    assert "<!doctype html" in response.text.lower()
