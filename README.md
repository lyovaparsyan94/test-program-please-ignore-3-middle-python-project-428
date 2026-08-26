# Бекенд для бронирования авиабилетов (Python)

[![hexlet-check](https://github.com/lyovaparsyan94/test-program-please-ignore-3-middle-python-project-428/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/lyovaparsyan94/test-program-please-ignore-3-middle-python-project-428/actions)
[![main](https://github.com/lyovaparsyan94/test-program-please-ignore-3-middle-python-project-428/actions/workflows/main.yml/badge.svg)](https://github.com/lyovaparsyan94/test-program-please-ignore-3-middle-python-project-428/actions/workflows/main.yml)

Реализуйте бекенд сервиса бронирования авиабилетов: справочник городов, поиск рейсов,
оформление, просмотр и отмену брони. Фреймворк выбираете сами, данные храните в PostgreSQL.
Фронтенд предоставляет Хекслет — готовое приложение, которое подключается к вашему API
и работает только тогда, когда API отвечает по описанному контракту.

Учебный проект Хекслета: https://ru.hexlet.io/programs/test-program-please-ignore-3-middle-python
Как это должно работать: https://files.hexlet.app/a/76p1kx

## Демо

Развёрнутое приложение: <!-- TODO: ссылка на Render, например https://flight-booking-xxxx.onrender.com -->

## Стек

- Python 3.13, FastAPI, Uvicorn
- PostgreSQL, psycopg 3, yoyo-migrations
- uv — менеджер зависимостей; Docker — запуск и деплой

## Требования

- Python 3.13, [uv](https://docs.astral.sh/uv/)
- PostgreSQL 16+ (или Docker)
- Node.js 22 — только чтобы установить npm-пакет с фронтендом

## Установка

```bash
git clone https://github.com/lyovaparsyan94/test-program-please-ignore-3-middle-python-project-428.git
cd test-program-please-ignore-3-middle-python-project-428
make install   # uv sync + npm ci
make build     # раскладывает статику фронтенда в public/
```

Переменные окружения:

- `DATABASE_URL` — строка подключения к PostgreSQL (по умолчанию `postgresql://flights:flights@localhost:5432/flights`)
- `PORT` — порт сервера (по умолчанию `8080`)

## Использование

```bash
make start   # применяет миграции, заливает справочные данные и запускает сервер
```

Приложение будет доступно на `http://localhost:8080`.

## Тесты

```bash
make test-api   # тесты API на pytest
make test       # браузерные тесты Хекслета (нужен запущенный сервер и APP_URL)
```

---

<details>
<summary>Автоматические тесты Хекслета</summary>

Тесты запускаются на каждый коммит. За запуск отвечает файл `.github/workflows/hexlet-check.yml` — не удаляйте и не переименовывайте ни его, ни репозиторий.

</details>

## О Хекслете

[Хекслет](https://ru.hexlet.io/) — школа программирования: авторские программы обучения с практикой, поддержкой наставников и реальными проектами, которые остаются в резюме. Этот репозиторий — один из таких проектов.
