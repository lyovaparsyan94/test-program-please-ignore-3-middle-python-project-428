import os


def get_database_url() -> str:
    # Без тихого дефолта на localhost: забытая переменная на Render даст
    # понятную ошибку, а не таймаут. Локально дефолт задаёт Makefile/conftest.
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL не задан")
    return url
