#
# API-РёРЅС‚РµРіСЂР°С†РёРѕРЅРЅС‹Рµ С‚РµСЃС‚С‹ РґР»СЏ projects-СЌРЅРґРїРѕРёРЅС‚РѕРІ.
#
# РЎС†РµРЅР°СЂРёРё: create в†’ list в†’ get в†’ add_user в†’ remove_user.
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


def _set_project_creator(project_id: str, user_id: str) -> None:
    _execute_sql(
        "UPDATE projects SET created_by = CAST(:user_id AS uuid) WHERE id = CAST(:project_id AS uuid)",
        {"project_id": project_id, "user_id": user_id},
    )


@allure.epic("Projects")
@allure.feature("РџСЂРѕРµРєС‚С‹ Рё СѓС‡Р°СЃС‚РЅРёРєРё")
class TestProjects:
    """CRUD Рё СѓС‡Р°СЃС‚РЅРёРєРё РїСЂРѕРµРєС‚РѕРІ."""

    @allure.story("РЎРѕР·РґР°РЅРёРµ РїСЂРѕРµРєС‚Р°")
    @allure.title("POST /projects СЃРѕР·РґР°С‘С‚ РїСЂРѕРµРєС‚ Рё РІРѕР·РІСЂР°С‰Р°РµС‚ 201")
    def test_create_project(self, client, auth_headers):
        key = _unique_project_key()
        with allure.step(f"POST /projects key={key}"):
            resp = client.post(
                "/api/v1/projects",
                headers=auth_headers,
                json={"key": key, "name": "Test Project"},
            )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "project" in data
        assert data["project"]["key"] == key
        assert data["project"]["name"] == "Test Project"
        assert "id" in data["project"]
        assert "created_at" in data["project"]
        assert data["project"]["current_user_role"] == "admin_project"

    @allure.story("РЎРїРёСЃРѕРє РїСЂРѕРµРєС‚РѕРІ")
    @allure.title("GET /projects РІРѕР·РІСЂР°С‰Р°РµС‚ items Рё total")
    def test_list_projects(self, client, auth_headers):
        key = _unique_project_key()
        create_resp = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "List Project"},
        )
        assert create_resp.status_code == 201, create_resp.text
        project_id = create_resp.json()["project"]["id"]

        resp = client.get(
            "/api/v1/projects",
            headers=auth_headers,
            params={"limit": 10, "offset": 0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        project = next(item for item in data["items"] if item["id"] == project_id)
        assert project["current_user_role"] == "admin_project"

    @allure.story("РџРѕР»СѓС‡РµРЅРёРµ РїСЂРѕРµРєС‚Р°")
    @allure.title("GET /projects/{id} РІРѕР·РІСЂР°С‰Р°РµС‚ РїСЂРѕРµРєС‚")
    def test_get_project(self, client, auth_headers):
        key = _unique_project_key()
        create_resp = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Proj"},
        )
        project_id = create_resp.json()["project"]["id"]
        resp = client.get(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["project"]["id"] == project_id
        assert resp.json()["project"]["key"] == key
        assert resp.json()["project"]["current_user_role"] == "admin_project"

    @allure.story("РџРµСЂСЃРѕРЅР°Р»СЊРЅС‹Рµ РЅР°СЃС‚СЂРѕР№РєРё")
    @allure.title("GET/PATCH /projects/{id}/me/preferences управляет new_employee_mode")
    def test_project_onboarding_preferences_roundtrip(self, client, auth_headers):
        key = _unique_project_key()
        create_resp = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Preferences Project"},
        )
        assert create_resp.status_code == 201, create_resp.text
        project_id = create_resp.json()["project"]["id"]

        get_default = client.get(
            f"/api/v1/projects/{project_id}/me/preferences",
            headers=auth_headers,
        )
        assert get_default.status_code == 200, get_default.text
        assert get_default.json()["preferences"]["new_employee_mode"] is False

        update = client.patch(
            f"/api/v1/projects/{project_id}/me/preferences",
            headers=auth_headers,
            json={"new_employee_mode": True},
        )
        assert update.status_code == 200, update.text
        assert update.json()["preferences"]["new_employee_mode"] is True

        get_updated = client.get(
            f"/api/v1/projects/{project_id}/me/preferences",
            headers=auth_headers,
        )
        assert get_updated.status_code == 200, get_updated.text
        assert get_updated.json()["preferences"]["new_employee_mode"] is True

    @allure.story("РџРµСЂСЃРѕРЅР°Р»СЊРЅС‹Рµ РЅР°СЃС‚СЂРѕР№РєРё")
    @allure.title("GET /projects/{id}/me/preferences недоступен для пользователя вне проекта")
    def test_project_onboarding_preferences_forbidden_for_non_member(self, client, auth_headers):
        key = _unique_project_key()
        create_resp = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Private Preferences Project"},
        )
        assert create_resp.status_code == 201, create_resp.text
        project_id = create_resp.json()["project"]["id"]

        outsider_email = _unique_email()
        outsider_reg = client.post(
            "/api/v1/auth/register",
            json={"email": outsider_email, "full_name": "Outsider", "password": "password123"},
        )
        assert outsider_reg.status_code == 201, outsider_reg.text
        outsider_headers, _ = _login_headers(client, outsider_email, "password123")

        resp = client.get(
            f"/api/v1/projects/{project_id}/me/preferences",
            headers=outsider_headers,
        )
        assert resp.status_code == 403, resp.text

    @allure.story("Р”РѕР±Р°РІР»РµРЅРёРµ СѓС‡Р°СЃС‚РЅРёРєР°")
    @allure.title("POST /projects/{id}/users РґРѕР±Р°РІР»СЏРµС‚ СѓС‡Р°СЃС‚РЅРёРєР°")
    def test_add_project_user(self, client, auth_headers):
        email = _unique_email()
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": "Member", "password": "password123"},
        )
        assert reg.status_code == 201, reg.text
        headers, _ = _login_headers(client, "demo.user@example.com", "demo12345")
        key = _unique_project_key()
        create_resp = client.post(
            "/api/v1/projects",
            headers=headers,
            json={"key": key, "name": "Proj"},
        )
        project_id = create_resp.json()["project"]["id"]
        _, member_id = _login_headers(client, email, "password123")
        with allure.step(f"POST /projects/{project_id}/users"):
            resp = client.post(
                f"/api/v1/projects/{project_id}/users",
                headers=headers,
                json={"user_id": member_id, "role": "user"},
            )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["project_id"] == project_id
        assert data["user_id"] == member_id
        assert data["role"] == "user"

    @allure.story("Р”РѕСЃС‚СѓРї Рє РїСЂРѕРµРєС‚Сѓ")
    @allure.title("GET /projects/{id} РґР»СЏ С‡СѓР¶РѕРіРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РІРѕР·РІСЂР°С‰Р°РµС‚ 403")
    def test_get_project_forbidden_for_non_member(self, client, auth_headers):
        key = _unique_project_key()
        create_resp = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Private Proj"},
        )
        assert create_resp.status_code == 201, create_resp.text
        project_id = create_resp.json()["project"]["id"]

        email = _unique_email()
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": "Other", "password": "password123"},
        )
        assert reg.status_code == 201, reg.text
        other_headers, _ = _login_headers(client, email, "password123")

        resp = client.get(f"/api/v1/projects/{project_id}", headers=other_headers)
        assert resp.status_code == 403

    @allure.story("Р РѕР»СЊ admin_project")
    @allure.title("POST /projects/{id}/users РґР»СЏ user РІРѕР·РІСЂР°С‰Р°РµС‚ 403")
    def test_add_project_user_requires_admin(self, client, auth_headers):
        owner_key = _unique_project_key()
        owner_proj = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": owner_key, "name": "Role Proj"},
        )
        assert owner_proj.status_code == 201, owner_proj.text
        project_id = owner_proj.json()["project"]["id"]

        member_email = _unique_email()
        member_reg = client.post(
            "/api/v1/auth/register",
            json={"email": member_email, "full_name": "Member", "password": "password123"},
        )
        assert member_reg.status_code == 201, member_reg.text
        member_headers, member_id = _login_headers(client, member_email, "password123")

        add_member = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=auth_headers,
            json={"user_id": member_id, "role": "user"},
        )
        assert add_member.status_code == 201, add_member.text

        another_email = _unique_email()
        another_reg = client.post(
            "/api/v1/auth/register",
            json={"email": another_email, "full_name": "Another", "password": "password123"},
        )
        assert another_reg.status_code == 201, another_reg.text
        _, another_id = _login_headers(client, another_email, "password123")

        denied = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=member_headers,
            json={"user_id": another_id, "role": "user"},
        )
        assert denied.status_code == 403

    @allure.story("Р В Р С•Р В»РЎРЉ admin_project")
    @allure.title("project member receives 403 on project admin actions")
    def test_project_admin_actions_require_admin_project(self, client, auth_headers):
        project_key = _unique_project_key()
        create_project = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": project_key, "name": "Admin Actions Project"},
        )
        assert create_project.status_code == 201, create_project.text
        project_id = create_project.json()["project"]["id"]

        member_email = _unique_email()
        member_reg = client.post(
            "/api/v1/auth/register",
            json={"email": member_email, "full_name": "Project Member", "password": "password123"},
        )
        assert member_reg.status_code == 201, member_reg.text
        member_headers, member_id = _login_headers(client, member_email, "password123")

        candidate_email = _unique_email()
        candidate_reg = client.post(
            "/api/v1/auth/register",
            json={"email": candidate_email, "full_name": "Candidate Member", "password": "password123"},
        )
        assert candidate_reg.status_code == 201, candidate_reg.text
        _, candidate_id = _login_headers(client, candidate_email, "password123")

        add_member = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=auth_headers,
            json={"user_id": member_id, "role": "user"},
        )
        assert add_member.status_code == 201, add_member.text

        add_candidate = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=auth_headers,
            json={"user_id": candidate_id, "role": "user"},
        )
        assert add_candidate.status_code == 201, add_candidate.text

        responses = {
            "update_project": client.patch(
                f"/api/v1/projects/{project_id}",
                headers=member_headers,
                json={"description": "forbidden"},
            ),
            "search_users": client.get(
                f"/api/v1/projects/{project_id}/users/search",
                headers=member_headers,
                params={"q": "Candidate", "limit": 10, "offset": 0},
            ),
            "promote_member": client.patch(
                f"/api/v1/projects/{project_id}/users/{candidate_id}",
                headers=member_headers,
                json={"role": "admin_project"},
            ),
            "remove_member": client.delete(
                f"/api/v1/projects/{project_id}/users/{candidate_id}",
                headers=member_headers,
            ),
        }

        for action_name, response in responses.items():
            assert response.status_code == 403, f"{action_name}: {response.text}"

    @allure.story("Р’РёСЂС‚СѓР°Р»СЊРЅС‹Р№ admin_project")
    @allure.title("admin_app РїСЂРѕС…РѕРґРёС‚ project-admin РїСЂРѕРІРµСЂРєРё Р±РµР· direct membership")
    def test_admin_app_has_virtual_admin_project_access(self, client):
        admin_headers, _ = _login_headers(client, "demo.user@example.com", "demo12345")

        member_email = _unique_email()
        member_reg = client.post(
            "/api/v1/auth/register",
            json={"email": member_email, "full_name": "Member", "password": "password123"},
        )
        assert member_reg.status_code == 201, member_reg.text
        _, member_id = _login_headers(client, member_email, "password123")

        key = _unique_project_key()
        create_resp = client.post(
            "/api/v1/projects",
            headers=admin_headers,
            json={"key": key, "name": "Admin App Project"},
        )
        assert create_resp.status_code == 201, create_resp.text
        project_id = create_resp.json()["project"]["id"]
        assert create_resp.json()["project"]["current_user_role"] == "admin_project"

        users_resp = client.get(f"/api/v1/projects/{project_id}/users", headers=admin_headers)
        assert users_resp.status_code == 200, users_resp.text
        assert users_resp.json()["total"] == 0
        assert users_resp.json()["items"] == []

        patch_resp = client.patch(
            f"/api/v1/projects/{project_id}",
            headers=admin_headers,
            json={"description": "updated by admin_app"},
        )
        assert patch_resp.status_code == 200, patch_resp.text
        assert patch_resp.json()["project"]["description"] == "updated by admin_app"

        add_member = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=admin_headers,
            json={"user_id": member_id, "role": "user"},
        )
        assert add_member.status_code == 201, add_member.text

    @allure.story("Р РѕР»СЊ admin_project")
    @allure.title("admin_project РїРѕР»СѓС‡Р°РµС‚ project-admin РїСЂР°РІР° РІ РєРѕРЅС‚СѓСЂРµ РїСЂРѕРµРєС‚Р°")
    def test_admin_project_member_can_manage_project_users(self, client, auth_headers):
        project_key = _unique_project_key()
        create_project = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": project_key, "name": "Admin Scope Project"},
        )
        assert create_project.status_code == 201, create_project.text
        project_id = create_project.json()["project"]["id"]

        admin_email = _unique_email()
        admin_reg = client.post(
            "/api/v1/auth/register",
            json={"email": admin_email, "full_name": "Project Admin", "password": "password123"},
        )
        assert admin_reg.status_code == 201, admin_reg.text
        admin_headers, admin_member_id = _login_headers(client, admin_email, "password123")

        viewer_email = _unique_email()
        viewer_reg = client.post(
            "/api/v1/auth/register",
            json={"email": viewer_email, "full_name": "Viewer", "password": "password123"},
        )
        assert viewer_reg.status_code == 201, viewer_reg.text
        _, viewer_id = _login_headers(client, viewer_email, "password123")

        add_admin = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=auth_headers,
            json={"user_id": admin_member_id, "role": "admin_project"},
        )
        assert add_admin.status_code == 201, add_admin.text

        add_viewer = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=admin_headers,
            json={"user_id": viewer_id, "role": "user"},
        )
        assert add_viewer.status_code == 201, add_viewer.text

    @allure.story("Р СќР В°РЎРѓРЎвЂљРЎР‚Р С•Р в„–Р С”Р С‘ Р С—РЎР‚Р С•Р ВµР С”РЎвЂљР В°")
    @allure.title("PATCH /projects/{id} обновляет name, description и category")
    def test_update_project_updates_name_description_category(self, client, auth_headers):
        key = _unique_project_key()
        create_resp = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Initial Project"},
        )
        assert create_resp.status_code == 201, create_resp.text
        project_id = create_resp.json()["project"]["id"]

        patch_resp = client.patch(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers,
            json={
                "name": "Renamed Project",
                "description": "Updated description",
                "category": "Business",
            },
        )
        assert patch_resp.status_code == 200, patch_resp.text
        project = patch_resp.json()["project"]
        assert project["name"] == "Renamed Project"
        assert project["description"] == "Updated description"
        assert project["category"] == "Business"
        assert project["current_user_role"] == "admin_project"

    @allure.story("Р СџР С•Р С‘РЎРѓР С” РЎС“РЎвЂЎР В°РЎРѓРЎвЂљР Р…Р С‘Р С”Р С•Р Р†")
    @allure.title("GET /projects/{id}/users/search возвращает доступных пользователей с app_role")
    def test_search_project_users_returns_available_members_with_app_role(self, client, auth_headers):
        key = _unique_project_key()
        search_token = _unique_project_key()
        create_resp = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Search Project"},
        )
        assert create_resp.status_code == 201, create_resp.text
        project_id = create_resp.json()["project"]["id"]

        existing_email = _unique_email()
        existing_reg = client.post(
            "/api/v1/auth/register",
            json={"email": existing_email, "full_name": "Existing Member", "password": "password123"},
        )
        assert existing_reg.status_code == 201, existing_reg.text
        _, existing_user_id = _login_headers(client, existing_email, "password123")

        candidate_email = _unique_email()
        candidate_reg = client.post(
            "/api/v1/auth/register",
            json={
                "email": candidate_email,
                "full_name": f"Search Candidate {search_token}",
                "password": "password123",
            },
        )
        assert candidate_reg.status_code == 201, candidate_reg.text
        _, candidate_user_id = _login_headers(client, candidate_email, "password123")

        add_existing = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=auth_headers,
            json={"user_id": existing_user_id, "role": "user"},
        )
        assert add_existing.status_code == 201, add_existing.text

        search_resp = client.get(
            f"/api/v1/projects/{project_id}/users/search",
            headers=auth_headers,
            params={"q": search_token, "limit": 10, "offset": 0},
        )
        assert search_resp.status_code == 200, search_resp.text
        data = search_resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == candidate_user_id
        assert data["items"][0]["app_role"] == "user"

    @allure.story("Удаление проекта")
    @allure.title("DELETE /projects/{id} удаляет пустой проект с участниками и убирает его из списка")
    def test_delete_empty_project(self, client, auth_headers):
        email = _unique_email()
        password = "password123"
        register = client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": "Project Owner", "password": password},
        )
        assert register.status_code == 201, register.text
        owner_headers, owner_id = _login_headers(client, email, password)
        _set_user_app_role(owner_id, "user")

        key = _unique_project_key()
        create_resp = client.post(
            "/api/v1/projects",
            headers=owner_headers,
            json={"key": key, "name": "Empty Project"},
        )
        assert create_resp.status_code == 201, create_resp.text
        project_id = create_resp.json()["project"]["id"]

        deleted = client.delete(f"/api/v1/projects/{project_id}", headers=owner_headers)
        assert deleted.status_code == 204, deleted.text

        get_deleted = client.get(f"/api/v1/projects/{project_id}", headers=owner_headers)
        assert get_deleted.status_code == 404, get_deleted.text

        listed = client.get("/api/v1/projects", headers=owner_headers)
        assert listed.status_code == 200, listed.text
        assert all(item["id"] != project_id for item in listed.json()["items"])

    @allure.story("Удаление проекта")
    @allure.title("DELETE /projects/{id} запрещает удалять проект с задачами")
    def test_cannot_delete_project_with_issues(self, client, auth_headers):
        key = _unique_project_key()
        create_resp = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Project With Issues"},
        )
        assert create_resp.status_code == 201, create_resp.text
        project_id = create_resp.json()["project"]["id"]

        statuses_resp = client.get(
            f"/api/v1/projects/{project_id}/statuses",
            headers=auth_headers,
        )
        assert statuses_resp.status_code == 200, statuses_resp.text
        status_id = statuses_resp.json()["items"][0]["id"]

        create_issue = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            json={"type": "task", "title": "Blocking task", "status_id": status_id},
        )
        assert create_issue.status_code == 201, create_issue.text

        deleted = client.delete(f"/api/v1/projects/{project_id}", headers=auth_headers)
        assert deleted.status_code == 409, deleted.text
        assert "есть задачи" in deleted.json()["error"]["message"]

    @allure.story("Р РЋР В±Р Р…Р С•Р Р†Р В»Р ВµР Р…Р С‘Р Вµ РЎР‚Р С•Р В»Р С‘ РЎС“РЎвЂЎР В°РЎРѓРЎвЂљР Р…Р С‘Р С”Р В°")
    @allure.title("PATCH /projects/{id}/users/{userId} изменяет роль участника")
    def test_update_project_user_changes_role(self, client, auth_headers):
        key = _unique_project_key()
        create_resp = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Role Update Project"},
        )
        assert create_resp.status_code == 201, create_resp.text
        project_id = create_resp.json()["project"]["id"]

        member_email = _unique_email()
        member_reg = client.post(
            "/api/v1/auth/register",
            json={"email": member_email, "full_name": "Role Candidate", "password": "password123"},
        )
        assert member_reg.status_code == 201, member_reg.text
        _, member_id = _login_headers(client, member_email, "password123")

        add_member = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=auth_headers,
            json={"user_id": member_id, "role": "user"},
        )
        assert add_member.status_code == 201, add_member.text

        update_member = client.patch(
            f"/api/v1/projects/{project_id}/users/{member_id}",
            headers=auth_headers,
            json={"role": "admin_project"},
        )
        assert update_member.status_code == 200, update_member.text
        assert update_member.json()["role"] == "admin_project"

    @allure.story("Р В Р С•Р В»РЎРЉ admin_project")
    @allure.title("Нельзя удалить последнего прямого admin_project участника")
    def test_cannot_remove_last_direct_admin_project_member(self, client, auth_headers):
        key = _unique_project_key()
        create_resp = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Last Direct Admin Delete"},
        )
        assert create_resp.status_code == 201, create_resp.text
        project_id = create_resp.json()["project"]["id"]

        admin_email = _unique_email()
        admin_reg = client.post(
            "/api/v1/auth/register",
            json={"email": admin_email, "full_name": "Direct Admin", "password": "password123"},
        )
        assert admin_reg.status_code == 201, admin_reg.text
        _, admin_id = _login_headers(client, admin_email, "password123")

        add_admin = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=auth_headers,
            json={"user_id": admin_id, "role": "admin_project"},
        )
        assert add_admin.status_code == 201, add_admin.text

        remove_admin = client.delete(
            f"/api/v1/projects/{project_id}/users/{admin_id}",
            headers=auth_headers,
        )
        assert remove_admin.status_code == 409, remove_admin.text
        assert "direct admin_project" in remove_admin.json()["error"]["message"]

    @allure.story("Р В Р С•Р В»РЎРЉ admin_project")
    @allure.title("Нельзя понизить последнего прямого admin_project участника")
    def test_cannot_downgrade_last_direct_admin_project_member(self, client, auth_headers):
        key = _unique_project_key()
        create_resp = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Last Direct Admin Downgrade"},
        )
        assert create_resp.status_code == 201, create_resp.text
        project_id = create_resp.json()["project"]["id"]

        admin_email = _unique_email()
        admin_reg = client.post(
            "/api/v1/auth/register",
            json={"email": admin_email, "full_name": "Direct Admin Downgrade", "password": "password123"},
        )
        assert admin_reg.status_code == 201, admin_reg.text
        _, admin_id = _login_headers(client, admin_email, "password123")

        add_admin = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=auth_headers,
            json={"user_id": admin_id, "role": "admin_project"},
        )
        assert add_admin.status_code == 201, add_admin.text

        downgrade_admin = client.patch(
            f"/api/v1/projects/{project_id}/users/{admin_id}",
            headers=auth_headers,
            json={"role": "user"},
        )
        assert downgrade_admin.status_code == 409, downgrade_admin.text
        assert "direct admin_project" in downgrade_admin.json()["error"]["message"]

    @allure.story("Project creation RBAC")
    @allure.title("admin_app can create a project without direct membership")
    def test_create_project_allowed_for_admin_app_without_direct_membership(self, client):
        email = _unique_email()
        register = client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": "Promoted Admin App", "password": "password123"},
        )
        assert register.status_code == 201, register.text
        headers, user_id = _login_headers(client, email, "password123")

        _set_user_app_role(user_id, "admin_app")

        resp = client.post(
            "/api/v1/projects",
            headers=headers,
            json={"key": _unique_project_key(), "name": "Admin App Create"},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["project"]["current_user_role"] == "admin_project"

    @allure.story("Project creation RBAC")
    @allure.title("direct admin_project membership allows project creation")
    def test_create_project_allowed_for_direct_admin_project_member(self, client, auth_headers):
        candidate_email = _unique_email()
        register = client.post(
            "/api/v1/auth/register",
            json={"email": candidate_email, "full_name": "Project Admin", "password": "password123"},
        )
        assert register.status_code == 201, register.text
        candidate_headers, candidate_id = _login_headers(client, candidate_email, "password123")

        bootstrap_project = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": _unique_project_key(), "name": "Bootstrap Project"},
        )
        assert bootstrap_project.status_code == 201, bootstrap_project.text
        bootstrap_project_id = bootstrap_project.json()["project"]["id"]

        add_admin = client.post(
            f"/api/v1/projects/{bootstrap_project_id}/users",
            headers=auth_headers,
            json={"user_id": candidate_id, "role": "admin_project"},
        )
        assert add_admin.status_code == 201, add_admin.text

        resp = client.post(
            "/api/v1/projects",
            headers=candidate_headers,
            json={"key": _unique_project_key(), "name": "Direct Admin Create"},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["project"]["current_user_role"] == "admin_project"

    @allure.story("Project creation RBAC")
    @allure.title("plain user can create a project")
    def test_create_project_allowed_for_plain_user(self, client):
        email = _unique_email()
        register = client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": "Plain User", "password": "password123"},
        )
        assert register.status_code == 201, register.text
        headers, _ = _login_headers(client, email, "password123")

        resp = client.post(
            "/api/v1/projects",
            headers=headers,
            json={"key": _unique_project_key(), "name": "Plain User Create"},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["project"]["current_user_role"] == "admin_project"

    @allure.story("Project creation RBAC")
    @allure.title("plain user can create project even if previously only created_by")
    def test_create_project_does_not_depend_on_created_by(self, client, auth_headers):
        email = _unique_email()
        register = client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": "Created By Only", "password": "password123"},
        )
        assert register.status_code == 201, register.text
        headers, user_id = _login_headers(client, email, "password123")

        bootstrap_project = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": _unique_project_key(), "name": "Created By Bootstrap"},
        )
        assert bootstrap_project.status_code == 201, bootstrap_project.text
        bootstrap_project_id = bootstrap_project.json()["project"]["id"]

        _set_project_creator(bootstrap_project_id, user_id)

        resp = client.post(
            "/api/v1/projects",
            headers=headers,
            json={"key": _unique_project_key(), "name": "Created By Can Create"},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["project"]["current_user_role"] == "admin_project"

    @allure.story("Project reports and dashboards")
    @allure.title("GET /projects/{id}/reports/dashboard returns project analytics for admins only")
    def test_project_dashboard_report_requires_admin_and_returns_metrics(self, client):
        owner_headers, _ = _login_headers(client, "demo.user@example.com", "demo12345")

        create_project = client.post(
            "/api/v1/projects",
            headers=owner_headers,
            json={"key": _unique_project_key(), "name": "Reporting Project"},
        )
        assert create_project.status_code == 201, create_project.text
        project_id = create_project.json()["project"]["id"]

        statuses_resp = client.get(f"/api/v1/projects/{project_id}/statuses", headers=owner_headers)
        assert statuses_resp.status_code == 200, statuses_resp.text
        statuses = statuses_resp.json()["items"]
        todo_status_id = next(item["id"] for item in statuses if item["category"] == "todo")
        in_progress_status_id = next(item["id"] for item in statuses if item["category"] == "in_progress")
        done_status_id = next(item["id"] for item in statuses if item["category"] == "done")

        member_email = _unique_email()
        member_register = client.post(
            "/api/v1/auth/register",
            json={"email": member_email, "full_name": "Report Member", "password": "password123"},
        )
        assert member_register.status_code == 201, member_register.text
        member_headers, member_id = _login_headers(client, member_email, "password123")

        add_member = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=owner_headers,
            json={"user_id": member_id, "role": "user"},
        )
        assert add_member.status_code == 201, add_member.text

        # task in TODO
        todo_issue = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=owner_headers,
            json={
                "type": "task",
                "title": "Todo task",
                "status_id": todo_status_id,
                "planned_hours": 4,
                "assignee_id": member_id,
            },
        )
        assert todo_issue.status_code == 201, todo_issue.text

        # task in progress
        in_progress_issue = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=owner_headers,
            json={
                "type": "task",
                "title": "In progress task",
                "status_id": in_progress_status_id,
                "planned_hours": 8,
                "assignee_id": member_id,
            },
        )
        assert in_progress_issue.status_code == 201, in_progress_issue.text
        in_progress_issue_id = in_progress_issue.json()["issue"]["id"]

        # task done
        done_issue = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=owner_headers,
            json={
                "type": "task",
                "title": "Done task",
                "status_id": done_status_id,
                "planned_hours": 2,
                "assignee_id": member_id,
            },
        )
        assert done_issue.status_code == 201, done_issue.text

        epic_issue = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=owner_headers,
            json={
                "type": "epic",
                "title": "Calendar epic",
                "status_id": in_progress_status_id,
                "assignee_id": member_id,
            },
        )
        assert epic_issue.status_code == 201, epic_issue.text
        epic_issue_id = epic_issue.json()["issue"]["id"]

        worklog = client.post(
            f"/api/v1/issues/{in_progress_issue_id}/worklogs",
            headers=member_headers,
            json={"work_date": "2026-04-20", "hours": 3.5, "comment": "Progress update"},
        )
        assert worklog.status_code == 201, worklog.text

        # calendar users can also log time against epic, dashboard must include it in actual hours
        epic_worklog = client.post(
            f"/api/v1/issues/{epic_issue_id}/worklogs",
            headers=member_headers,
            json={"work_date": "2026-04-20", "hours": 2, "comment": "Calendar effort"},
        )
        assert epic_worklog.status_code == 201, epic_worklog.text

        report = client.get(
            f"/api/v1/projects/{project_id}/reports/dashboard",
            headers=owner_headers,
            params={"recent_days": 30, "overdue_limit": 10},
        )
        assert report.status_code == 200, report.text
        data = report.json()
        assert data["project_id"] == project_id
        assert data["task_summary"]["total"] == 3
        assert data["task_summary"]["completed"] == 1
        assert data["task_summary"]["in_progress"] == 1
        assert data["task_summary"]["not_started"] == 1
        assert len(data["tasks_by_assignee"]) >= 1
        assert data["effort_summary"]["planned_hours"] == 14
        assert data["effort_summary"]["actual_hours"] == 5.5
        assert "status_distribution" in data
        assert "overdue" in data
        assert "workload" in data
        assert "recent_activity" in data

        csv_export = client.get(
            f"/api/v1/projects/{project_id}/reports/dashboard/export",
            headers=owner_headers,
            params={"format": "csv", "recent_days": 30, "overdue_limit": 10},
        )
        assert csv_export.status_code == 200, csv_export.text
        assert csv_export.headers["content-type"].startswith("text/csv")
        assert 'attachment; filename="project-dashboard-' in csv_export.headers["content-disposition"]
        assert csv_export.headers["content-disposition"].endswith('.csv"')
        csv_payload = csv_export.content.decode("utf-8-sig")
        assert "section,entity,metric,value" in csv_payload
        assert "task_summary,project,total,3" in csv_payload

        excel_export = client.get(
            f"/api/v1/projects/{project_id}/reports/dashboard/export",
            headers=owner_headers,
            params={"format": "excel"},
        )
        assert excel_export.status_code == 200, excel_export.text
        assert excel_export.headers["content-type"].startswith("application/vnd.ms-excel")
        assert 'attachment; filename="project-dashboard-' in excel_export.headers["content-disposition"]
        assert excel_export.headers["content-disposition"].endswith('.xls"')
        excel_payload = excel_export.content.decode("utf-8-sig")
        assert "<table border='1'>" in excel_payload
        assert "task_summary" in excel_payload

        forbidden = client.get(
            f"/api/v1/projects/{project_id}/reports/dashboard",
            headers=member_headers,
        )
        assert forbidden.status_code == 403, forbidden.text

        forbidden_export = client.get(
            f"/api/v1/projects/{project_id}/reports/dashboard/export",
            headers=member_headers,
            params={"format": "csv"},
        )
        assert forbidden_export.status_code == 403, forbidden_export.text


@allure.epic("Projects")
@allure.feature("Onboarding assignees")
@allure.story("Onboarding assignees")
@allure.title("GET/PATCH /projects/{id}/onboarding/assignees manages onboarding visibility by members")
def test_project_onboarding_assignees_roundtrip(client, auth_headers):
    key = _unique_project_key()
    create_resp = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"key": key, "name": "Onboarding Assignees Project"},
    )
    assert create_resp.status_code == 201, create_resp.text
    project_id = create_resp.json()["project"]["id"]

    first_email = _unique_email()
    first_reg = client.post(
        "/api/v1/auth/register",
        json={"email": first_email, "full_name": "First Assignee", "password": "password123"},
    )
    assert first_reg.status_code == 201, first_reg.text
    _, first_user_id = _login_headers(client, first_email, "password123")

    second_email = _unique_email()
    second_reg = client.post(
        "/api/v1/auth/register",
        json={"email": second_email, "full_name": "Second Assignee", "password": "password123"},
    )
    assert second_reg.status_code == 201, second_reg.text
    _, second_user_id = _login_headers(client, second_email, "password123")

    add_first = client.post(
        f"/api/v1/projects/{project_id}/users",
        headers=auth_headers,
        json={"user_id": first_user_id, "role": "user"},
    )
    assert add_first.status_code == 201, add_first.text
    add_second = client.post(
        f"/api/v1/projects/{project_id}/users",
        headers=auth_headers,
        json={"user_id": second_user_id, "role": "user"},
    )
    assert add_second.status_code == 201, add_second.text

    empty_resp = client.get(
        f"/api/v1/projects/{project_id}/onboarding/assignees",
        headers=auth_headers,
    )
    assert empty_resp.status_code == 200, empty_resp.text
    assert empty_resp.json()["assignees"] == []

    set_first = client.patch(
        f"/api/v1/projects/{project_id}/onboarding/assignees",
        headers=auth_headers,
        json={"user_ids": [first_user_id]},
    )
    assert set_first.status_code == 200, set_first.text
    assert [item["user_id"] for item in set_first.json()["assignees"]] == [first_user_id]

    set_second = client.patch(
        f"/api/v1/projects/{project_id}/onboarding/assignees",
        headers=auth_headers,
        json={"user_ids": [second_user_id]},
    )
    assert set_second.status_code == 200, set_second.text
    assert [item["user_id"] for item in set_second.json()["assignees"]] == [second_user_id]

    first_headers, _ = _login_headers(client, first_email, "password123")
    first_preferences = client.get(
        f"/api/v1/projects/{project_id}/me/preferences",
        headers=first_headers,
    )
    assert first_preferences.status_code == 200, first_preferences.text
    assert first_preferences.json()["preferences"]["new_employee_mode"] is False

    second_headers, _ = _login_headers(client, second_email, "password123")
    second_preferences = client.get(
        f"/api/v1/projects/{project_id}/me/preferences",
        headers=second_headers,
    )
    assert second_preferences.status_code == 200, second_preferences.text
    assert second_preferences.json()["preferences"]["new_employee_mode"] is True
