from datetime import date as date_cls
from pathlib import Path

from fastapi import Body, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from app.bookings import (
    cancel_booking,
    create_booking,
    get_booking,
    validate_payload,
)
from app.cities import list_cities
from app.db import get_db
from app.flights import get_flight, search_flights

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"code": code, "message": message}, status_code=status_code)


def validation_error(message: str) -> JSONResponse:
    return error_response(400, "validation_error", message)


def not_found(message: str) -> JSONResponse:
    return error_response(404, "not_found", message)


def create_app() -> FastAPI:
    app = FastAPI()

    # FastAPI по умолчанию отдаёт 422 {"detail": [...]}, а контракт требует
    # 400 {"code": "validation_error", ...}. Переопределяем один раз.
    @app.exception_handler(RequestValidationError)
    def on_validation_error(request: Request, exc: RequestValidationError):
        return validation_error("Некорректные параметры запроса")

    @app.get("/api/cities")
    def get_cities(conn=Depends(get_db)):
        return list_cities(conn)

    @app.get("/api/flights")
    def get_flights(
        origin: str | None = None,
        destination: str | None = None,
        date: str | None = None,
        passengers: str | None = None,
        conn=Depends(get_db),
    ):
        if not origin or not destination or not date:
            return validation_error("origin, destination и date обязательны")
        try:
            departure_date = date_cls.fromisoformat(date)
        except ValueError:
            return validation_error("date должен быть в формате YYYY-MM-DD")

        passengers_count = 1
        if passengers is not None:
            try:
                passengers_count = int(passengers)
            except ValueError:
                return validation_error("passengers должен быть целым числом")
        if passengers_count < 1:
            return validation_error("passengers должен быть не меньше 1")

        return search_flights(conn, origin, destination, departure_date, passengers_count)

    @app.get("/api/flights/{flight_id}")
    def get_flight_by_id(flight_id: str, conn=Depends(get_db)):
        flight = get_flight(conn, flight_id)
        if flight is None:
            return not_found("Рейс не найден")
        return flight

    @app.post("/api/bookings")
    def post_booking(body: dict = Body(...), conn=Depends(get_db)):
        data, error = validate_payload(body)
        if error is not None:
            return validation_error(error)

        flight = get_flight(conn, data["flightId"])
        if flight is None:
            return validation_error("Рейс не найден")

        booking = create_booking(conn, flight, data["contact"], data["passengers"])
        return JSONResponse(booking, status_code=201)

    @app.get("/api/bookings/{code}")
    def get_booking_by_code(code: str, lastName: str | None = None, conn=Depends(get_db)):
        booking = get_booking(conn, code, lastName)
        if booking is None:
            return not_found("Бронь не найдена")
        return booking

    @app.post("/api/bookings/{code}/cancel")
    def cancel_booking_by_code(
        code: str, body: dict | None = Body(default=None), conn=Depends(get_db)
    ):
        last_name = body.get("lastName") if isinstance(body, dict) else None
        booking = cancel_booking(conn, code, last_name)
        if booking is None:
            return not_found("Бронь не найдена")
        return booking

    # Неизвестный путь внутри /api/ — это JSON-404, а не index.html.
    # HEAD обязателен: без него HEAD-запрос к /api/... проваливается в SPA-fallback
    # ниже и получает 200 с index.html вместо JSON-404 (в т.ч. на существующих ручках).
    @app.api_route(
        "/api/{path:path}",
        methods=["GET", "HEAD", "POST", "DELETE", "PUT", "PATCH"],
    )
    def api_not_found(path: str):
        return not_found("Ресурс не найден")

    # SPA-fallback — обязательно последним маршрутом, после всех /api/...
    # HEAD нужен: статику проверяют `curl -sI`, а браузер шлёт HEAD за ассетами.
    @app.api_route("/{path:path}", methods=["GET", "HEAD"])
    def spa(path: str):
        file = (PUBLIC_DIR / path).resolve()
        # is_relative_to обязателен: путь приходит из запроса,
        # и `..` в нём увёл бы за пределы public.
        if path and file.is_relative_to(PUBLIC_DIR) and file.is_file():
            return FileResponse(file)

        return FileResponse(PUBLIC_DIR / "index.html")

    return app
