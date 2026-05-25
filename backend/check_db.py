
# Скрипт проверки доступа к БД из бэкенда.
# Запуск из корня проекта: python -m backend.check_db

import asyncio
import sys

from sqlalchemy import text

from backend.database import engine


async def check_db() -> bool:
    # Проверяет подключение к БД: выполняет простой запрос SELECT 1.
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Ошибка доступа к БД: {e}", file=sys.stderr)
        return False
    finally:
        await engine.dispose()


def main() -> None:
    ok = asyncio.run(check_db())
    if ok:
        print("OK: подключение к БД успешно.")
        sys.exit(0)
    else:
        print("FAIL: нет доступа к БД.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
