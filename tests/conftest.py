import os

# Тесты ходят в реальную базу. Локально подставляем дефолт (docker-контейнер
# flights-db); в CI DATABASE_URL уже задан и setdefault его не трогает.
os.environ.setdefault(
    "DATABASE_URL", "postgresql://flights:flights@localhost:5432/flights"
)

import pytest  # noqa: E402

from app.migrate import apply_migrations  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    """Схема и справочные данные должны существовать до тестов API."""
    apply_migrations()
    seed()
