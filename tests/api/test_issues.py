#
# API-интеграционные тесты для issues-эндпоинтов.
#
# Сценарии: create → list → get by key → get by id → update → delete.
from __future__ import annotations

import allure
import pytest

from conftest import _unique_email, _unique_project_key


def _login_headers(client, email: str, password: str) -> tuple[dict[str, str], str]:
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    data = login.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]["id"]


@allure.epic("Issues")
@allure.feature("Задачи и эпики")
class TestIssues:
    """CRUD задач в проекте."""

    @allure.story("Создание epic")
    @allure.title("POST /projects/{id}/issues создаёт epic для MVP «Новый сотрудник»")
    def test_create_new_employee_onboarding_epic(self, client, auth_headers):
        key = _unique_project_key()
        create_proj = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Onboarding MVP"},
        )
        assert create_proj.status_code == 201, create_proj.text
        project_id = create_proj.json()["project"]["id"]

        statuses_resp = client.get(
            f"/api/v1/projects/{project_id}/statuses",
            headers=auth_headers,
        )
        assert statuses_resp.status_code == 200, statuses_resp.text
        status_id = statuses_resp.json()["items"][0]["id"]

        payload = {
            "type": "epic",
            "title": "Режим «Новый сотрудник»: авто-onboarding (MVP)",
            "description": (
                "Система автоматически рекомендует: что читать (Wiki), какие задачи посмотреть (Issues), "
                "кто ключевые люди (Users). Только на основе данных проекта (активность, связи, роли), "
                "без вручную написанных гайдов."
            ),
            "status_id": status_id,
        }
        resp = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            json=payload,
        )
        assert resp.status_code == 201, resp.text
        issue = resp.json()["issue"]
        assert issue["type"] == "epic"
        assert issue["title"] == payload["title"]
        assert issue["description"] == payload["description"]
        assert issue["status_id"] == status_id

    @allure.story("Создание задачи")
    @allure.title("POST /projects/{id}/issues создаёт задачу с автогенерированным ключом")
    def test_create_issue(self, client, auth_headers):
        key = _unique_project_key()
        create_proj = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Proj"},
        )
        assert create_proj.status_code == 201, create_proj.text
        project_id = create_proj.json()["project"]["id"]
        statuses_resp = client.get(
            f"/api/v1/projects/{project_id}/statuses",
            headers=auth_headers,
        )
        status_id = statuses_resp.json()["items"][0]["id"]
        criticalities = client.get("/api/v1/criticalities", headers=auth_headers)
        crit_id = criticalities.json()["items"][0]["id"] if criticalities.json()["items"] else None
        with allure.step("POST /projects/{id}/issues"):
            payload = {
                "type": "task",
                "title": "Test task",
                "status_id": status_id,
            }
            if crit_id:
                payload["criticality_id"] = crit_id
            resp = client.post(
                f"/api/v1/projects/{project_id}/issues",
                headers=auth_headers,
                json=payload,
            )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "issue" in data
        assert data["issue"]["title"] == "Test task"
        assert "key" in data["issue"]
        assert data["issue"]["key"].startswith(key)
        assert "id" in data["issue"]

    @allure.story("Иерархия задач")
    @allure.title("task может наследоваться от другой task и epic")
    def test_create_task_with_task_parent(self, client, auth_headers):
        key = _unique_project_key()
        create_proj = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Hierarchy Project"},
        )
        assert create_proj.status_code == 201, create_proj.text
        project_id = create_proj.json()["project"]["id"]

        statuses = client.get(
            f"/api/v1/projects/{project_id}/statuses",
            headers=auth_headers,
        )
        assert statuses.status_code == 200, statuses.text
        status_id = statuses.json()["items"][0]["id"]

        epic_resp = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            json={"type": "epic", "title": "Root epic", "status_id": status_id},
        )
        assert epic_resp.status_code == 201, epic_resp.text
        epic_id = epic_resp.json()["issue"]["id"]

        parent_task_resp = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            json={
                "type": "task",
                "title": "Parent task",
                "status_id": status_id,
                "parent_id": epic_id,
            },
        )
        assert parent_task_resp.status_code == 201, parent_task_resp.text
        parent_task_id = parent_task_resp.json()["issue"]["id"]
        assert parent_task_resp.json()["issue"]["parent_id"] == epic_id

        child_task_resp = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            json={
                "type": "task",
                "title": "Child task",
                "status_id": status_id,
                "parent_id": parent_task_id,
            },
        )
        assert child_task_resp.status_code == 201, child_task_resp.text
        assert child_task_resp.json()["issue"]["parent_id"] == parent_task_id

    @allure.story("Иерархия задач")
    @allure.title("PATCH /issues/{id} запрещает циклическую иерархию parent_id")
    def test_update_issue_rejects_parent_cycle(self, client, auth_headers):
        key = _unique_project_key()
        create_proj = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Cycle Project"},
        )
        assert create_proj.status_code == 201, create_proj.text
        project_id = create_proj.json()["project"]["id"]

        statuses = client.get(
            f"/api/v1/projects/{project_id}/statuses",
            headers=auth_headers,
        )
        assert statuses.status_code == 200, statuses.text
        status_id = statuses.json()["items"][0]["id"]

        parent_issue = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            json={"type": "task", "title": "Parent", "status_id": status_id},
        )
        assert parent_issue.status_code == 201, parent_issue.text
        parent_issue_id = parent_issue.json()["issue"]["id"]

        child_issue = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            json={
                "type": "task",
                "title": "Child",
                "status_id": status_id,
                "parent_id": parent_issue_id,
            },
        )
        assert child_issue.status_code == 201, child_issue.text
        child_issue_id = child_issue.json()["issue"]["id"]

        cyclic_update = client.patch(
            f"/api/v1/issues/{parent_issue_id}",
            headers=auth_headers,
            json={"parent_id": child_issue_id},
        )
        assert cyclic_update.status_code == 400, cyclic_update.text

    @allure.story("Список задач")
    @allure.title("GET /projects/{id}/issues возвращает items и total")
    def test_list_issues(self, client, auth_headers):
        key = _unique_project_key()
        create_proj = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "P"},
        )
        assert create_proj.status_code == 201, create_proj.text
        project_id = create_proj.json()["project"]["id"]
        resp = client.get(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            params={"limit": 10, "offset": 0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    @allure.story("Получение по ключу")
    @allure.title("GET /projects/{id}/issues/by-key/{key} возвращает задачу")
    def test_get_issue_by_key(self, client, auth_headers):
        key = _unique_project_key()
        create_proj = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "P"},
        )
        assert create_proj.status_code == 201, create_proj.text
        project_id = create_proj.json()["project"]["id"]
        statuses = client.get(
            f"/api/v1/projects/{project_id}/statuses",
            headers=auth_headers,
        )
        status_id = statuses.json()["items"][0]["id"]
        create_issue = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            json={"type": "task", "title": "Find me", "status_id": status_id},
        )
        assert create_issue.status_code == 201, create_issue.text
        issue_key = create_issue.json()["issue"]["key"]
        resp = client.get(
            f"/api/v1/projects/{project_id}/issues/by-key/{issue_key}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["issue"]["key"] == issue_key
        assert resp.json()["issue"]["title"] == "Find me"

    @allure.story("Обновление задачи")
    @allure.title("PATCH /issues/{id} обновляет задачу")
    def test_update_issue(self, client, auth_headers):
        key = _unique_project_key()
        create_proj = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "P"},
        )
        assert create_proj.status_code == 201, create_proj.text
        project_id = create_proj.json()["project"]["id"]
        statuses = client.get(
            f"/api/v1/projects/{project_id}/statuses",
            headers=auth_headers,
        )
        status_id = statuses.json()["items"][0]["id"]
        create_issue = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            json={"type": "task", "title": "Original", "status_id": status_id},
        )
        assert create_issue.status_code == 201, create_issue.text
        issue_id = create_issue.json()["issue"]["id"]
        resp = client.patch(
            f"/api/v1/issues/{issue_id}",
            headers=auth_headers,
            json={"title": "Updated title"},
        )
        assert resp.status_code == 200
        assert resp.json()["issue"]["title"] == "Updated title"

    @allure.story("Трудозатраты задачи")
    @allure.title("GET /issues/{id} возвращает planned/logged hours в карточке задачи")
    def test_get_issue_details_returns_worklog_summary(self, client, auth_headers):
        key = _unique_project_key()
        create_proj = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Effort Project"},
        )
        assert create_proj.status_code == 201, create_proj.text
        project_id = create_proj.json()["project"]["id"]

        statuses = client.get(
            f"/api/v1/projects/{project_id}/statuses",
            headers=auth_headers,
        )
        assert statuses.status_code == 200, statuses.text
        status_id = statuses.json()["items"][0]["id"]

        create_issue = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            json={
                "type": "task",
                "title": "Track effort",
                "status_id": status_id,
                "planned_hours": 8,
            },
        )
        assert create_issue.status_code == 201, create_issue.text
        issue_id = create_issue.json()["issue"]["id"]

        create_worklog = client.post(
            f"/api/v1/issues/{issue_id}/worklogs",
            headers=auth_headers,
            json={"work_date": "2026-04-20", "hours": 3.5, "comment": "Work in progress"},
        )
        assert create_worklog.status_code == 201, create_worklog.text

        details = client.get(f"/api/v1/issues/{issue_id}", headers=auth_headers)
        assert details.status_code == 200, details.text
        body = details.json()
        assert body["issue"]["planned_hours"] == 8
        assert body["issue"]["logged_hours"] == 3.5
        assert body["worklog_summary"]["planned_hours"] == 8
        assert body["worklog_summary"]["logged_hours"] == 3.5

        listed = client.get(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            params={"limit": 10, "offset": 0},
        )
        assert listed.status_code == 200, listed.text
        item = next(row for row in listed.json()["items"] if row["id"] == issue_id)
        assert item["logged_hours"] == 3.5

    @allure.story("Удаление задачи")
    @allure.title("DELETE /issues/{id} удаляет задачу и убирает её из списка проекта")
    def test_delete_issue(self, client, auth_headers):
        key = _unique_project_key()
        create_proj = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Delete Issue Project"},
        )
        assert create_proj.status_code == 201, create_proj.text
        project_id = create_proj.json()["project"]["id"]

        statuses = client.get(
            f"/api/v1/projects/{project_id}/statuses",
            headers=auth_headers,
        )
        assert statuses.status_code == 200, statuses.text
        status_id = statuses.json()["items"][0]["id"]

        create_issue = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            json={"type": "task", "title": "Disposable issue", "status_id": status_id},
        )
        assert create_issue.status_code == 201, create_issue.text
        issue_id = create_issue.json()["issue"]["id"]

        deleted = client.delete(f"/api/v1/issues/{issue_id}", headers=auth_headers)
        assert deleted.status_code == 204, deleted.text

        details = client.get(f"/api/v1/issues/{issue_id}", headers=auth_headers)
        assert details.status_code == 404, details.text

        listed = client.get(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            params={"limit": 10, "offset": 0},
        )
        assert listed.status_code == 200, listed.text
        assert all(item["id"] != issue_id for item in listed.json()["items"])

    @allure.story("RBAC for project users")
    @allure.title("project user can list/create/update issues while outsider gets 403")
    def test_project_user_issue_access_and_outsider_forbidden(self, client):
        admin_headers, _ = _login_headers(client, "demo.user@example.com", "demo12345")

        create_proj = client.post(
            "/api/v1/projects",
            headers=admin_headers,
            json={"key": _unique_project_key(), "name": "Issue RBAC Project"},
        )
        assert create_proj.status_code == 201, create_proj.text
        project_id = create_proj.json()["project"]["id"]

        statuses = client.get(
            f"/api/v1/projects/{project_id}/statuses",
            headers=admin_headers,
        )
        assert statuses.status_code == 200, statuses.text
        status_id = statuses.json()["items"][0]["id"]

        project_admin_email = _unique_email()
        project_admin_register = client.post(
            "/api/v1/auth/register",
            json={
                "email": project_admin_email,
                "full_name": "Issue Project Admin",
                "password": "password123",
            },
        )
        assert project_admin_register.status_code == 201, project_admin_register.text
        project_admin_headers, project_admin_id = _login_headers(
            client, project_admin_email, "password123"
        )

        promote_project_admin = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=admin_headers,
            json={"user_id": project_admin_id, "role": "admin_project"},
        )
        assert promote_project_admin.status_code == 201, promote_project_admin.text

        project_user_email = _unique_email()
        project_user_register = client.post(
            "/api/v1/auth/register",
            json={
                "email": project_user_email,
                "full_name": "Issue Project User",
                "password": "password123",
            },
        )
        assert project_user_register.status_code == 201, project_user_register.text
        project_user_headers, project_user_id = _login_headers(
            client, project_user_email, "password123"
        )

        outsider_email = _unique_email()
        outsider_register = client.post(
            "/api/v1/auth/register",
            json={
                "email": outsider_email,
                "full_name": "Issue Outsider",
                "password": "password123",
            },
        )
        assert outsider_register.status_code == 201, outsider_register.text
        outsider_headers, _ = _login_headers(client, outsider_email, "password123")

        add_project_user = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=project_admin_headers,
            json={"user_id": project_user_id, "role": "user"},
        )
        assert add_project_user.status_code == 201, add_project_user.text

        list_for_project_user = client.get(
            f"/api/v1/projects/{project_id}/issues",
            headers=project_user_headers,
            params={"limit": 20, "offset": 0},
        )
        assert list_for_project_user.status_code == 200, list_for_project_user.text

        create_issue = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=project_user_headers,
            json={"type": "task", "title": "Project user task", "status_id": status_id},
        )
        assert create_issue.status_code == 201, create_issue.text
        issue_id = create_issue.json()["issue"]["id"]

        create_epic = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=project_user_headers,
            json={
                "type": "epic",
                "title": "Режим «Новый сотрудник»: авто-onboarding (MVP)",
                "description": (
                    "Система автоматически рекомендует: что читать (Wiki), какие задачи посмотреть (Issues), "
                    "кто ключевые люди (Users). Только на основе данных проекта (активность, связи, роли), "
                    "без вручную написанных гайдов."
                ),
                "status_id": status_id,
            },
        )
        assert create_epic.status_code == 201, create_epic.text
        assert create_epic.json()["issue"]["type"] == "epic"

        update_issue = client.patch(
            f"/api/v1/issues/{issue_id}",
            headers=project_user_headers,
            json={"title": "Project user updated task"},
        )
        assert update_issue.status_code == 200, update_issue.text
        assert update_issue.json()["issue"]["title"] == "Project user updated task"

        outsider_list = client.get(
            f"/api/v1/projects/{project_id}/issues",
            headers=outsider_headers,
            params={"limit": 20, "offset": 0},
        )
        assert outsider_list.status_code == 403, outsider_list.text

        outsider_create = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=outsider_headers,
            json={"type": "task", "title": "Forbidden issue", "status_id": status_id},
        )
        assert outsider_create.status_code == 403, outsider_create.text

        outsider_create_epic = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=outsider_headers,
            json={"type": "epic", "title": "Forbidden epic", "status_id": status_id},
        )
        assert outsider_create_epic.status_code == 403, outsider_create_epic.text

        outsider_update = client.patch(
            f"/api/v1/issues/{issue_id}",
            headers=outsider_headers,
            json={"title": "Forbidden update"},
        )
        assert outsider_update.status_code == 403, outsider_update.text
