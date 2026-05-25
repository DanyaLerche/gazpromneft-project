## Task Tracker Demo

Демо-проект трекера задач в формате Task Tracker с канбан-доской.

- **Backend**: FastAPI + PostgreSQL, Alembic-миграции, асинхронный SQLAlchemy.
- **Frontend**: Angular + Akita + ng-zorro.
- **Хранилище файлов**: MinIO.

### Быстрый запуск через Docker

- **1. Создать файл окружения**
  ```bash
  touch .env
  ```

  Для локального запуска файл может оставаться пустым: настройки PostgreSQL
  и MinIO уже указаны в `docker-compose.yaml`.

- **2. Запустить сервисы**
  ```bash
  docker compose up --build
  ```

- **3. Открыть приложения**
  - Angular-фронтенд: `http://localhost:4200`
  - Backend Swagger: `http://localhost:8000/docs`
  - Swagger UI: `http://localhost:8080`
  - MinIO Console: `http://localhost:9001`

После применения миграций в базе появится демо-проект `DEMO` с
пользователями и задачами, которые отображаются на доске и в списках.

### Демо-пользователи

- `demo.user@example.com` / `demo12345`
- `dev.one@example.com` / `12345`

### Остановка сервисов

```bash
docker compose down
```

Для полного удаления локальной базы и загруженных файлов:

```bash
docker compose down -v
```

> Регистрация новых пользователей требует настроенного SMTP в `.env`.
> Без SMTP можно использовать готовые демо-учётные записи.
