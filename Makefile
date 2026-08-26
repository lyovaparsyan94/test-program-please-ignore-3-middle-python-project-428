FRONTEND_DIST = node_modules/@hexlet/python-flight-booking-frontend/dist

install:
	uv sync
	npm ci

build:
	rm -rf public/assets public/index.html
	cp -R $(FRONTEND_DIST)/. public/

migrate:
	uv run python -m app.migrate

seed:
	uv run python -m app.seed

start: migrate seed
	uv run uvicorn --factory app.main:create_app --host 0.0.0.0 --port $${PORT:-8080}

test:
	npx playwright test

test-api:
	uv run pytest

contract:
	npx tsp compile contract

.PHONY: install build start migrate seed test test-api contract
