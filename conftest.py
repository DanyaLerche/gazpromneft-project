# Быстрое хэширование в тестах (PBKDF2 100 итераций вместо 200000).
# На Windows фикс UnicodeDecodeError при подключении к PostgreSQL.
import os
os.environ["AUTH_PBKDF2_ITERATIONS"] = "100"
os.environ.setdefault("PGCLIENTENCODING", "UTF8")

import pytest


def _get_app():
    from backend.main import app
    return app


def _db_available() -> tuple[bool, str]:
    """Проверка доступности PostgreSQL в отдельном процессе (не трогаем event loop приложения)."""
    import subprocess
    import sys
    code = """
import asyncio
from sqlalchemy import text
from backend.database import engine

async def _():
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))

asyncio.run(_())
"""
    try:
        r = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            timeout=10,
            env={**os.environ, "PGCLIENTENCODING": os.environ.get("PGCLIENTENCODING", "UTF8")},
            cwd=os.path.dirname(os.path.abspath(__file__)) or ".",
        )
        if r.returncode == 0:
            return True, ""
        err = (r.stderr or r.stdout or b"").decode("utf-8", errors="replace")
        return False, err.strip() or "Unknown error"
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def pytest_collection_modifyitems(config, items):
    """Пропуск api/contract тестов, если БД недоступна. Отключить: PYTEST_SKIP_DB=0 pytest ..."""
    if os.environ.get("PYTEST_SKIP_DB", "1") == "0":
        return  # не проверяем БД, тесты выполняются в любом случае
    ok, err = _db_available()
    if not ok:
        reason = f"PostgreSQL недоступна: {err}" if err else "PostgreSQL недоступна — запустите БД и проверьте .env"
        skip_db = pytest.mark.skip(reason=reason)
        for item in items:
            if "api" in str(item.fspath) or "contract" in str(item.fspath):
                item.add_marker(skip_db)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    app = _get_app()
    try:
        with TestClient(app) as c:
            yield c
    except (ConnectionResetError, OSError) as e:
        pytest.skip(f"Приложение не стартует (БД?): {e}")


@pytest.fixture
def auth_headers(client):
    """Bearer-токен для demo-пользователя (demo.user@example.com / demo12345)."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "demo.user@example.com", "password": "demo12345"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _unique_email():
    import uuid
    return f"test-{uuid.uuid4().hex[:12]}@example.com"


def _unique_project_key():
    import uuid
    return f"TST{uuid.uuid4().hex[:4].upper()}"
