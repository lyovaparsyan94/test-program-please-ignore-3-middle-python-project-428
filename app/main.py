from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse, JSONResponse

from app.db import get_db

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"


def create_app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/cities")
    def get_cities(conn=Depends(get_db)):
        rows = conn.execute(
            "SELECT code, name, country FROM cities ORDER BY position"
        ).fetchall()
        return rows

    # Неизвестный путь внутри /api/ — это JSON-404, а не index.html.
    @app.api_route("/api/{path:path}", methods=["GET", "POST", "DELETE", "PUT", "PATCH"])
    def api_not_found(path: str):
        return JSONResponse({"detail": "Not Found"}, status_code=404)

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
