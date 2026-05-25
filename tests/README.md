# Тесты

## Структура

```
tests/
├── unit/           # Unit-тесты (без БД, без HTTP)
│   └── test_auth_security.py
├── api/            # API integration-тесты (HTTP + БД)
│   ├── test_auth.py
│   ├── test_projects.py
│   └── test_issues.py
├── contract/       # Contract-тесты (ответы соответствуют OpenAPI)
│   └── test_openapi.py
└── README.md
```

## Запуск

**Важно:** Запускайте pytest **из корня проекта**, а не из папки `tests/`. Иначе `pytest tests/api/` ищет несуществующий путь `tests/tests/api/`.

```powershell
# Из корня проекта (gazpromneft-project-platform/)
cd C:\Users\zwel\PycharmProjects\gazprom\gazpromneft-project-platform
pytest                    # Все тесты
pytest tests/unit/        # Только unit (без БД)
pytest tests/api/         # Только API (нужна БД)
pytest tests/contract/    # Только contract

# С Allure-отчётом
pytest --alluredir=allure-results
allure serve allure-results   # требует Java + Allure CLI
```

**Если вы уже в папке `tests/`** — используйте пути без префикса `tests/`:
```powershell
cd tests
pytest          # Все тесты
pytest unit/    # Только unit
pytest api/     # Только API
pytest contract/
```

Если `allure` не найден: Allure CLI ставится отдельно (не через pip). Варианты: [scoop](https://scoop.sh) `scoop install allure`, [Chocolatey](https://chocolatey.org) `choco install allure`, или [ручная установка](https://allurereport.org/docs/gettingstarted-installation/). Нужна Java.

## Требования

- **Unit-тесты**: Python + зависимости. `AUTH_PBKDF2_ITERATIONS=100` подставляется в conftest для скорости. БД не нужна.
- **API и contract**: PostgreSQL (та же БД, что и для приложения). Миграции должны быть применены. Demo-пользователь: `demo.user@example.com` / `demo12345`. Если БД недоступна, эти тесты автоматически пропускаются (skip).

## Troubleshooting

### Тесты api/contract скипаются при работающем PostgreSQL

Проверка БД на Windows может давать ложный отрицательный результат (UnicodeDecodeError, "connection was closed"). **Отключите проверку и выполните тесты принудительно:**

```powershell
# Windows PowerShell
$env:PYTEST_SKIP_DB="0"; pytest tests/api/ -v
```

```cmd
# CMD
set PYTEST_SKIP_DB=0
pytest tests/api/
```

### ConnectionResetError / WinError 64 при PYTEST_SKIP_DB=0

Связано с сетевым подключением к PostgreSQL на Windows:

1. **`127.0.0.1` вместо `localhost`** — в `.env` задайте `DB_HOST=127.0.0.1`.
2. **PostgreSQL в Docker** — возможны проблемы с портами; предпочтительно локальный инсталл для тестов.
3. **Антивирус/файрвол** — могут разрывать соединение; проверьте исключения для localhost.
4. **Проверка приложения** — убедитесь, что `uvicorn backend.main:app` успешно стартует. Если приложение работает, тесты с тем же `.env` тоже должны пройти.
5. **Диагностика** — `python check_db.py` в корне проекта.

### asgi_lifespan / ModuleNotFoundError

Используется `TestClient` из Starlette, модуль `asgi-lifespan` не нужен.

### RuntimeError: Event loop is closed / AttributeError: 'NoneType' has no attribute 'send'

Проверка БД выполняется в отдельном subprocess, чтобы не портить event loop приложения. Если ошибка появляется на первом api/contract-тесте:

1. Перезапустите терминал.
2. При необходимости: `$env:PYTEST_SKIP_DB="0"; pytest` (обход проверки БД).
3. Убедитесь, что в корне проекта один `conftest.py` и в нём нет `from asgi_lifespan import LifespanManager`.

## Allure

Декораторы: `@allure.epic`, `@allure.feature`, `@allure.story`, `@allure.title`, `@allure.step`, `@allure.description`.
