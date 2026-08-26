FRONTEND_DIST = node_modules/@hexlet/python-flight-booking-frontend/dist

install:
	uv sync
	npm ci

build:
	rm -rf public/assets public/index.html
	cp -R $(FRONTEND_DIST)/. public/

start:
	uv run uvicorn --factory app.main:create_app --host 0.0.0.0 --port $${PORT:-8080}

test:
	npm test

contract:
	npx tsp compile contract

.PHONY: install build start test contract
