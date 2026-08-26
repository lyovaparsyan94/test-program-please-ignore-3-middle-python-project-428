from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def test_cities_returns_200_and_json_array():
    response = client.get("/api/cities")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body == []


def test_unknown_api_path_returns_json_404():
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
