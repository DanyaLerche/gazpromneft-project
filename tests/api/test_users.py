from __future__ import annotations

import allure
from sqlalchemy import create_engine, text

from config import settings
from conftest import _unique_email, _unique_project_key


def _login_headers(client, email: str, password: str) -> tuple[dict[str, str], str]:
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    data = login.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]["id"]


def _execute_sql(statement: str, params: dict[str, str]) -> None:
    engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", "+psycopg2"))
    try:
        with engine.begin() as connection:
            connection.execute(text("SET search_path TO tracker, public"))
            connection.execute(text(statement), params)
    finally:
        engine.dispose()


def _set_user_app_role(user_id: str, role: str) -> None:
    _execute_sql(
        "UPDATE users SET app_role = :role WHERE id = CAST(:user_id AS uuid)",
        {"role": role, "user_id": user_id},
    )


def _get_active_admin_app_user_ids() -> list[str]:
    engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", "+psycopg2"))
    try:
        with engine.begin() as connection:
            connection.execute(text("SET search_path TO tracker, public"))
            rows = connection.execute(
                text(
                    """
                    SELECT id::text
                    FROM users
                    WHERE app_role = 'admin_app'
                      AND is_active = true
                    ORDER BY created_at
                    """
                )
            ).fetchall()
    finally:
        engine.dispose()

    return [row[0] for row in rows]


@allure.epic("Users")
@allure.feature("Platform RBAC")
class TestPlatformUsers:
    @allure.story("List platform users")
    @allure.title("GET /users is available only for admin_app")
    def test_list_platform_users_requires_admin_app(self, client):
        admin_headers, _ = _login_headers(client, "demo.user@example.com", "demo12345")

        project_key = _unique_project_key()
        create_project = client.post(
            "/api/v1/projects",
            headers=admin_headers,
            json={"key": project_key, "name": "Platform Users Scope"},
        )
        assert create_project.status_code == 201, create_project.text
        project_id = create_project.json()["project"]["id"]

        project_admin_email = _unique_email()
        project_admin_register = client.post(
            "/api/v1/auth/register",
            json={
                "email": project_admin_email,
                "full_name": "Scoped Admin",
                "password": "password123",
            },
        )
        assert project_admin_register.status_code == 201, project_admin_register.text
        project_admin_headers, project_admin_id = _login_headers(
            client, project_admin_email, "password123"
        )

        add_project_admin = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=admin_headers,
            json={"user_id": project_admin_id, "role": "admin_project"},
        )
        assert add_project_admin.status_code == 201, add_project_admin.text

        plain_user_email = _unique_email()
        plain_user_register = client.post(
            "/api/v1/auth/register",
            json={
                "email": plain_user_email,
                "full_name": "Plain Platform User",
                "password": "password123",
            },
        )
        assert plain_user_register.status_code == 201, plain_user_register.text
        plain_user_headers, _ = _login_headers(client, plain_user_email, "password123")

        allowed = client.get(
            "/api/v1/users",
            headers=admin_headers,
            params={"q": "Platform User", "app_role": "user", "limit": 20, "offset": 0},
        )
        assert allowed.status_code == 200, allowed.text
        data = allowed.json()
        assert data["total"] >= 1
        assert any(item["email"] == plain_user_email for item in data["items"])
        assert all("app_role" in item for item in data["items"])

        denied_project_admin = client.get("/api/v1/users", headers=project_admin_headers)
        assert denied_project_admin.status_code == 403, denied_project_admin.text

        denied_plain_user = client.get("/api/v1/users", headers=plain_user_headers)
        assert denied_plain_user.status_code == 403, denied_plain_user.text

    @allure.story("Update app role")
    @allure.title("PATCH /users/{user_id} is available only for admin_app")
    def test_update_platform_user_requires_admin_app(self, client):
        admin_headers, _ = _login_headers(client, "demo.user@example.com", "demo12345")

        project_key = _unique_project_key()
        create_project = client.post(
            "/api/v1/projects",
            headers=admin_headers,
            json={"key": project_key, "name": "Role Update Scope"},
        )
        assert create_project.status_code == 201, create_project.text
        project_id = create_project.json()["project"]["id"]

        project_admin_email = _unique_email()
        project_admin_register = client.post(
            "/api/v1/auth/register",
            json={
                "email": project_admin_email,
                "full_name": "Project Admin Only",
                "password": "password123",
            },
        )
        assert project_admin_register.status_code == 201, project_admin_register.text
        project_admin_headers, project_admin_id = _login_headers(
            client, project_admin_email, "password123"
        )

        add_project_admin = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=admin_headers,
            json={"user_id": project_admin_id, "role": "admin_project"},
        )
        assert add_project_admin.status_code == 201, add_project_admin.text

        target_email = _unique_email()
        target_register = client.post(
            "/api/v1/auth/register",
            json={
                "email": target_email,
                "full_name": "Target User",
                "password": "password123",
            },
        )
        assert target_register.status_code == 201, target_register.text
        plain_user_headers, target_id = _login_headers(client, target_email, "password123")

        denied_project_admin = client.patch(
            f"/api/v1/users/{target_id}",
            headers=project_admin_headers,
            json={"app_role": "admin_app"},
        )
        assert denied_project_admin.status_code == 403, denied_project_admin.text

        denied_plain_user = client.patch(
            f"/api/v1/users/{target_id}",
            headers=plain_user_headers,
            json={"app_role": "admin_app"},
        )
        assert denied_plain_user.status_code == 403, denied_plain_user.text

        allowed = client.patch(
            f"/api/v1/users/{target_id}",
            headers=admin_headers,
            json={"app_role": "admin_app"},
        )
        assert allowed.status_code == 200, allowed.text
        assert allowed.json()["app_role"] == "admin_app"

        cleanup = client.patch(
            f"/api/v1/users/{target_id}",
            headers=admin_headers,
            json={"app_role": "user"},
        )
        assert cleanup.status_code == 200, cleanup.text

    @allure.story("Promotion flow")
    @allure.title("user promoted to admin_app gets global project access without re-login")
    def test_promoted_admin_app_gets_global_access_without_new_login(self, client):
        admin_headers, _ = _login_headers(client, "demo.user@example.com", "demo12345")

        first_project = client.post(
            "/api/v1/projects",
            headers=admin_headers,
            json={"key": _unique_project_key(), "name": "Global Access One"},
        )
        assert first_project.status_code == 201, first_project.text
        first_project_id = first_project.json()["project"]["id"]

        second_project = client.post(
            "/api/v1/projects",
            headers=admin_headers,
            json={"key": _unique_project_key(), "name": "Global Access Two"},
        )
        assert second_project.status_code == 201, second_project.text
        second_project_id = second_project.json()["project"]["id"]

        candidate_email = _unique_email()
        candidate_register = client.post(
            "/api/v1/auth/register",
            json={
                "email": candidate_email,
                "full_name": "Future Admin App",
                "password": "password123",
            },
        )
        assert candidate_register.status_code == 201, candidate_register.text
        candidate_headers, candidate_id = _login_headers(client, candidate_email, "password123")

        before_promotion = client.get("/api/v1/projects", headers=candidate_headers)
        assert before_promotion.status_code == 200, before_promotion.text
        assert all(
            item["id"] not in {first_project_id, second_project_id}
            for item in before_promotion.json()["items"]
        )

        promote = client.patch(
            f"/api/v1/users/{candidate_id}",
            headers=admin_headers,
            json={"app_role": "admin_app"},
        )
        assert promote.status_code == 200, promote.text
        assert promote.json()["app_role"] == "admin_app"

        after_promotion = client.get("/api/v1/projects", headers=candidate_headers)
        assert after_promotion.status_code == 200, after_promotion.text
        returned_ids = {item["id"] for item in after_promotion.json()["items"]}
        assert {first_project_id, second_project_id}.issubset(returned_ids)
        for item in after_promotion.json()["items"]:
            if item["id"] in {first_project_id, second_project_id}:
                assert item["current_user_role"] == "admin_project"

        direct_project_access = client.get(
            f"/api/v1/projects/{first_project_id}",
            headers=candidate_headers,
        )
        assert direct_project_access.status_code == 200, direct_project_access.text
        assert direct_project_access.json()["project"]["current_user_role"] == "admin_project"

        cleanup = client.patch(
            f"/api/v1/users/{candidate_id}",
            headers=admin_headers,
            json={"app_role": "user"},
        )
        assert cleanup.status_code == 200, cleanup.text

    @allure.story("Demotion flow")
    @allure.title("admin_app demotion removes virtual access but keeps direct project memberships")
    def test_demoted_admin_app_keeps_direct_memberships(self, client):
        admin_headers, _ = _login_headers(client, "demo.user@example.com", "demo12345")

        direct_project = client.post(
            "/api/v1/projects",
            headers=admin_headers,
            json={"key": _unique_project_key(), "name": "Direct Membership Project"},
        )
        assert direct_project.status_code == 201, direct_project.text
        direct_project_id = direct_project.json()["project"]["id"]

        hidden_project = client.post(
            "/api/v1/projects",
            headers=admin_headers,
            json={"key": _unique_project_key(), "name": "Virtual Access Project"},
        )
        assert hidden_project.status_code == 201, hidden_project.text
        hidden_project_id = hidden_project.json()["project"]["id"]

        candidate_email = _unique_email()
        candidate_register = client.post(
            "/api/v1/auth/register",
            json={
                "email": candidate_email,
                "full_name": "Direct Member Admin App",
                "password": "password123",
            },
        )
        assert candidate_register.status_code == 201, candidate_register.text
        candidate_headers, candidate_id = _login_headers(client, candidate_email, "password123")

        add_direct_member = client.post(
            f"/api/v1/projects/{direct_project_id}/users",
            headers=admin_headers,
            json={"user_id": candidate_id, "role": "user"},
        )
        assert add_direct_member.status_code == 201, add_direct_member.text

        promote = client.patch(
            f"/api/v1/users/{candidate_id}",
            headers=admin_headers,
            json={"app_role": "admin_app"},
        )
        assert promote.status_code == 200, promote.text

        admin_app_view = client.get("/api/v1/projects", headers=candidate_headers)
        assert admin_app_view.status_code == 200, admin_app_view.text
        admin_app_ids = {item["id"] for item in admin_app_view.json()["items"]}
        assert {direct_project_id, hidden_project_id}.issubset(admin_app_ids)

        demote = client.patch(
            f"/api/v1/users/{candidate_id}",
            headers=admin_headers,
            json={"app_role": "user"},
        )
        assert demote.status_code == 200, demote.text
        assert demote.json()["app_role"] == "user"

        after_demotion = client.get("/api/v1/projects", headers=candidate_headers)
        assert after_demotion.status_code == 200, after_demotion.text
        after_demotion_ids = {item["id"] for item in after_demotion.json()["items"]}
        assert direct_project_id in after_demotion_ids
        assert hidden_project_id not in after_demotion_ids

        direct_access = client.get(
            f"/api/v1/projects/{direct_project_id}",
            headers=candidate_headers,
        )
        assert direct_access.status_code == 200, direct_access.text
        assert direct_access.json()["project"]["current_user_role"] == "user"

        hidden_access = client.get(
            f"/api/v1/projects/{hidden_project_id}",
            headers=candidate_headers,
        )
        assert hidden_access.status_code == 403, hidden_access.text

    @allure.story("Last admin safeguard")
    @allure.title("Cannot remove admin_app from the last active admin_app user")
    def test_cannot_demote_last_admin_app(self, client):
        admin_headers, _ = _login_headers(client, "demo.user@example.com", "demo12345")

        candidate_email = _unique_email()
        candidate_register = client.post(
            "/api/v1/auth/register",
            json={
                "email": candidate_email,
                "full_name": "Last Admin Candidate",
                "password": "password123",
            },
        )
        assert candidate_register.status_code == 201, candidate_register.text
        candidate_headers, candidate_id = _login_headers(client, candidate_email, "password123")
        original_admin_ids = _get_active_admin_app_user_ids()

        try:
            promote = client.patch(
                f"/api/v1/users/{candidate_id}",
                headers=admin_headers,
                json={"app_role": "admin_app"},
            )
            assert promote.status_code == 200, promote.text

            for user_id in original_admin_ids:
                _set_user_app_role(user_id, "user")

            blocked = client.patch(
                f"/api/v1/users/{candidate_id}",
                headers=candidate_headers,
                json={"app_role": "user"},
            )
            assert blocked.status_code == 409, blocked.text
            assert "at least one active admin_app" in blocked.json()["error"]["message"]
        finally:
            _set_user_app_role(candidate_id, "user")
            for user_id in original_admin_ids:
                _set_user_app_role(user_id, "admin_app")
