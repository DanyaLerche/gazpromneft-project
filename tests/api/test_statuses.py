#
# API-интеграционные тесты для statuses-эндпоинтов.
from __future__ import annotations

import allure

from conftest import _unique_email, _unique_project_key


@allure.epic("Statuses")
@allure.feature("Роли доступа")
class TestStatusesRoles:
    @allure.story("Роль project_admin")
    @allure.title("POST /projects/{id}/statuses для project_member возвращает 403")
    def test_create_status_requires_admin(self, client, auth_headers):
        key = _unique_project_key()
        create_proj = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Statuses Proj"},
        )
        assert create_proj.status_code == 201, create_proj.text
        project_id = create_proj.json()["project"]["id"]

        member_email = _unique_email()
        member_reg = client.post(
            "/api/v1/auth/register",
            json={"email": member_email, "full_name": "Member", "password": "password123"},
        )
        assert member_reg.status_code == 201, member_reg.text
        member_login = client.post(
            "/api/v1/auth/login",
            json={"email": member_email, "password": "password123"},
        )
        assert member_login.status_code == 200, member_login.text
        member_id = member_login.json()["user"]["id"]

        add_member = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=auth_headers,
            json={"user_id": member_id, "role": "user"},
        )
        assert add_member.status_code == 201, add_member.text
        member_headers = {"Authorization": f"Bearer {member_login.json()['access_token']}"}

        denied = client.post(
            f"/api/v1/projects/{project_id}/statuses",
            headers=member_headers,
            json={"name": "Review", "category": "in_progress", "sort_order": 99},
        )
        assert denied.status_code == 403
