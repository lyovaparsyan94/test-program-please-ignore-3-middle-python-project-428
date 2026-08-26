# 1) Собранный фронтенд Хекслета — забираем из npm-пакета
FROM node:22-alpine AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# 2) Рантайм
FROM python:3.13-slim

# uv ставит зависимости по uv.lock — тот же менеджер, что и локально
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv

# make нужен, потому что образ запускается через `make start` — той же командой, что локально
RUN apt-get update \
    && apt-get install -y --no-install-recommends make \
    && rm -rf /var/lib/apt/lists/*

# Логи без буферизации: иначе вывод приложения виснет в буфере, пока процесс жив, и логи на Render
# пусты ровно тогда, когда нужны — при разборе упавшего деплоя.
ENV PYTHONUNBUFFERED=1
# Кеш uv и окружение проекта лежат на разных слоях образа, hardlink между ними невозможен
ENV UV_LINK_MODE=copy

WORKDIR /app

# --frozen: ставим ровно то, что в uv.lock. --no-dev: pytest и линтер в проде не нужны
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
COPY --from=frontend /build/node_modules/@hexlet/python-flight-booking-frontend/dist/. ./public/

CMD ["make", "start"]
