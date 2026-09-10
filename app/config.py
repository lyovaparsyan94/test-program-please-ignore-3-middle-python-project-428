import os


def get_database_url() -> str:
    """DSN для приложения (psycopg). Берётся из DATABASE_URL.

    Без тихого дефолта на localhost: забытая переменная на Render должна дать
    понятную ошибку конфигурации, а не таймаут подключения к localhost.
    Локальный запуск и тесты подставляют дефолт через Makefile и conftest.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL не задан. Укажите строку подключения к PostgreSQL "
            "в переменной окружения DATABASE_URL."
        )
    return url
