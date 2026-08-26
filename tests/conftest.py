import pytest

from app.migrate import apply_migrations
from app.seed import seed


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    """Схема и справочные данные должны существовать до тестов API."""
    apply_migrations()
    seed()
