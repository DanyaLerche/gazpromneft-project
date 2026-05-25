#
# API-РёРЅС‚РµРіСЂР°С†РёРѕРЅРЅС‹Рµ С‚РµСЃС‚С‹ РґР»СЏ auth-СЌРЅРґРїРѕРёРЅС‚РѕРІ.
#
# РџСЂРѕРІРµСЂСЏСЋС‚ РїРѕР»РЅС‹Р№ flow: register в†’ login в†’ me в†’ refresh в†’ logout.
# РЎС†РµРЅР°СЂРёРё РёСЃРїРѕР»СЊР·СѓСЋС‚ СѓРЅРёРєР°Р»СЊРЅС‹Рµ email, С‡С‚РѕР±С‹ С‚РµСЃС‚С‹ Р±С‹Р»Рё РЅРµР·Р°РІРёСЃРёРјС‹.
from __future__ import annotations

import asyncio
from uuid import UUID

import allure
from sqlalchemy import create_engine, select, text

from backend.database import async_session_maker
from backend.models import User
from config import settings
from conftest import _unique_email, _unique_project_key


async def _set_user_app_role(user_id: str, role: str) -> None:
    async with async_session_maker() as session:
        user = (await session.execute(select(User).where(User.id == UUID(user_id)))).scalar_one()
        user.app_role = role
        await session.commit()


def _set_user_app_role(user_id: str, role: str) -> None:
    engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", "+psycopg2"))
    try:
        with engine.begin() as connection:
            connection.execute(text("SET search_path TO tracker, public"))
            connection.execute(
                text("UPDATE users SET app_role = :role WHERE id = CAST(:user_id AS uuid)"),
                {"role": role, "user_id": user_id},
            )
    finally:
        engine.dispose()


@allure.epic("Auth")
@allure.feature("Р РµРіРёСЃС‚СЂР°С†РёСЏ Рё Р°СѓС‚РµРЅС‚РёС„РёРєР°С†РёСЏ")
class TestAuthFlow:
    """РџРѕР»РЅС‹Р№ СЃС†РµРЅР°СЂРёР№: СЂРµРіРёСЃС‚СЂР°С†РёСЏ в†’ Р»РѕРіРёРЅ в†’ РїСЂРѕС„РёР»СЊ в†’ refresh в†’ logout."""

    @allure.story("Р РµРіРёСЃС‚СЂР°С†РёСЏ")
    @allure.title("Р РµРіРёСЃС‚СЂР°С†РёСЏ РЅРѕРІРѕРіРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РІРѕР·РІСЂР°С‰Р°РµС‚ 201 Рё user")
    def test_register_returns_201_and_user(self, client):
        email = _unique_email()
        with allure.step(f"POST /auth/register СЃ email={email}"):
            resp = client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "full_name": "Test User",
                    "password": "password123",
                },
            )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "user" in data
        assert data["user"]["email"].lower() == email.lower()
        assert data["user"]["full_name"] == "Test User"
        assert "id" in data["user"]
        assert "created_at" in data["user"]
        assert "is_active" in data["user"]
        assert data["user"]["app_role"] == "user"

    @allure.story("Р РµРіРёСЃС‚СЂР°С†РёСЏ")
    @allure.title("Р”СѓР±Р»РёРєР°С‚ email РІРѕР·РІСЂР°С‰Р°РµС‚ 409")
    def test_register_duplicate_email_409(self, client):
        email = _unique_email()
        payload = {"email": email, "full_name": "First", "password": "password123"}
        with allure.step("РџРµСЂРІР°СЏ СЂРµРіРёСЃС‚СЂР°С†РёСЏ"):
            r1 = client.post("/api/v1/auth/register", json=payload)
        assert r1.status_code == 201
        with allure.step("Р’С‚РѕСЂР°СЏ СЂРµРіРёСЃС‚СЂР°С†РёСЏ СЃ С‚РµРј Р¶Рµ email"):
            r2 = client.post("/api/v1/auth/register", json=payload)
        assert r2.status_code == 409

    @allure.story("Р›РѕРіРёРЅ")
    @allure.title("Р›РѕРіРёРЅ РІРѕР·РІСЂР°С‰Р°РµС‚ access_token, refresh_token, user")
    def test_login_returns_tokens(self, client):
        email = _unique_email()
        password = "secretpass123"
        with allure.step("Р РµРіРёСЃС‚СЂР°С†РёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"):
            client.post(
                "/api/v1/auth/register",
                json={"email": email, "full_name": "User", "password": password},
            )
        with allure.step("POST /auth/login"):
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"].lower() == email.lower()
        assert data["user"]["app_role"] == "user"

    @allure.story("Р›РѕРіРёРЅ")
    @allure.title("Seed-РїРѕР»СЊР·РѕРІР°С‚РµР»СЊ dev.one@example.com РјРѕР¶РµС‚ РІРѕР№С‚Рё")
    def test_seeded_developer_one_can_login(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "dev.one@example.com", "password": "12345"},
        )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["user"]["email"] == "dev.one@example.com"
        assert data["user"]["app_role"] == "user"
        assert data["user"]["full_name"] == "Р Р°Р·СЂР°Р±РѕС‚С‡РёРє РћРґРёРЅ"
        assert "access_token" in data
        assert "refresh_token" in data

    @allure.story("Р›РѕРіРёРЅ")
    @allure.title("РќРµРІРµСЂРЅС‹Р№ РїР°СЂРѕР»СЊ РІРѕР·РІСЂР°С‰Р°РµС‚ 400")
    def test_seeded_developer_one_can_login(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "dev.one@example.com", "password": "12345"},
        )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["user"]["email"] == "dev.one@example.com"
        assert data["user"]["app_role"] == "user"
        assert data["user"]["full_name"]
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_bad_password_400(self, client):
        email = _unique_email()
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": "U", "password": "correct"},
        )
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "wrong"},
        )
        assert resp.status_code == 400

    @allure.story("РџСЂРѕС„РёР»СЊ")
    @allure.title("GET /me СЃ Bearer РІРѕР·РІСЂР°С‰Р°РµС‚ РїСЂРѕС„РёР»СЊ")
    def test_me_returns_profile(self, client, auth_headers):
        with allure.step("GET /me СЃ Authorization: Bearer"):
            resp = client.get("/api/v1/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "user" in data
        assert data["user"]["email"] == "demo.user@example.com"
        assert data["user"]["app_role"] == "admin_app"
        assert data["user"]["avatar_url"] is None

    @allure.story("РџСЂРѕС„РёР»СЊ")
    @allure.title("PATCH /me/profile обновляет глобальный аватар пользователя")
    def test_update_my_profile_avatar(self, client, auth_headers):
        avatar_url = "data:image/png;base64,ZmFrZS1hdmF0YXI="

        updated = client.patch(
            "/api/v1/me/profile",
            headers=auth_headers,
            json={"avatar_url": avatar_url},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["user"]["avatar_url"] == avatar_url

        profile = client.get("/api/v1/me", headers=auth_headers)
        assert profile.status_code == 200, profile.text
        assert profile.json()["user"]["avatar_url"] == avatar_url

        cleared = client.patch(
            "/api/v1/me/profile",
            headers=auth_headers,
            json={"avatar_url": ""},
        )
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["user"]["avatar_url"] is None

    @allure.story("РџСЂРѕС„РёР»СЊ")
    @allure.title("GET /me Р±РµР· С‚РѕРєРµРЅР° РІРѕР·РІСЂР°С‰Р°РµС‚ 401")
    def test_me_without_token_401(self, client):
        resp = client.get("/api/v1/me")
        assert resp.status_code == 401

    @allure.story("Refresh")
    @allure.title("POST /auth/refresh РІРѕР·РІСЂР°С‰Р°РµС‚ РЅРѕРІС‹Рµ С‚РѕРєРµРЅС‹")
    def test_refresh_returns_new_tokens(self, client):
        email = _unique_email()
        password = "password123"
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": "U", "password": password},
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_resp.status_code == 200, login_resp.text
        data = login_resp.json()
        assert "refresh_token" in data, f"Login response: {data}"
        refresh_token = data["refresh_token"]
        with allure.step("POST /auth/refresh"):
            resp = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != refresh_token

    @allure.story("Logout")
    @allure.title("POST /auth/logout РІРѕР·РІСЂР°С‰Р°РµС‚ 204")
    def test_logout_204(self, client, auth_headers):
        with allure.step("POST /auth/logout СЃ Bearer"):
            resp = client.post("/api/v1/auth/logout", headers=auth_headers)
        assert resp.status_code == 204

    @allure.story("JWT roles")
    @allure.title("РџСЂР°РІР° РґРѕСЃС‚СѓРїР° РїРµСЂРµС‡РёС‚С‹РІР°СЋС‚СЃСЏ РёР· Р‘Р” РґР»СЏ СѓР¶Рµ РІС‹РґР°РЅРЅРѕРіРѕ JWT")
    def test_roles_are_loaded_from_db_not_from_jwt(self, client):
        email = _unique_email()
        password = "password123"
        register = client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": "Role Switch", "password": password},
        )
        assert register.status_code == 201, register.text

        login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        data = login.json()
        user_id = data["user"]["id"]
        headers = {"Authorization": f"Bearer {data['access_token']}"}

        denied = client.post(
            "/api/v1/projects",
            headers=headers,
            json={"key": _unique_project_key(), "name": "Denied Before Promotion"},
        )
        assert denied.status_code == 403, denied.text

        _set_user_app_role(user_id, "admin_app")

        allowed = client.post(
            "/api/v1/projects",
            headers=headers,
            json={"key": _unique_project_key(), "name": "Allowed After Promotion"},
        )
        assert allowed.status_code == 201, allowed.text
        assert allowed.json()["project"]["current_user_role"] == "admin_project"

        profile = client.get("/api/v1/me", headers=headers)
        assert profile.status_code == 200, profile.text
        assert profile.json()["user"]["app_role"] == "admin_app"
