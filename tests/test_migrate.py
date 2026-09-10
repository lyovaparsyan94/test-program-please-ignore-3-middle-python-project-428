from app.migrate import _yoyo_url


def test_yoyo_url_rewrites_postgresql_scheme():
    assert _yoyo_url("postgresql://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"


def test_yoyo_url_rewrites_postgres_scheme():
    assert _yoyo_url("postgres://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"


def test_yoyo_url_passes_other_schemes_through():
    assert _yoyo_url("sqlite:///db.sqlite") == "sqlite:///db.sqlite"
