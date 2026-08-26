from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def _date_ahead(days: int) -> str:
    return (datetime.now(timezone.utc).date() + timedelta(days=days)).isoformat()


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
