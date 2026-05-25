## Task Tracker Demo 

Демо‑проект трекера задач в формате Task Tracker с канбан‑доской.

- **Backend**: FastAPI + PostgreSQL, Alembic‑миграции, асинхронный SQLAlchemy.
- **Frontend**: Angular + Akita + ng-zorro.

### Быстрый запуск через Docker

- **1. Запуск сервисов**
  ```bash
  docker-compose up --build
  ```

- **2. Открыть приложения**
  - Backend Swagger: `http://localhost:8000/docs`
  - Angular‑фронтенд: `http://localhost:4200`

После применения миграций в базе появится демо‑проект `DEMO` с несколькими пользователями и задачами, которые отображаются на доске и в списках.

