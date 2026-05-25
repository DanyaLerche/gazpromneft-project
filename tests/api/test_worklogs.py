from __future__ import annotations

from datetime import date

import allure
import pytest

from conftest import _unique_email, _unique_project_key


def _login_headers(client, email: str, password: str) -> tuple[dict[str, str], str]:
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    data = login.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]["id"]


def _register_and_login(client, full_name: str) -> tuple[dict[str, str], str]:
    email = _unique_email()
    password = "password123"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": full_name, "password": password},
    )
    assert reg.status_code == 201, reg.text
    return _login_headers(client, email, password)


def _create_project_and_issue(client, headers: dict[str, str]) -> tuple[str, str]:
    key = _unique_project_key()
    create_proj = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"key": key, "name": "Worklogs Project"},
    )
    assert create_proj.status_code == 201, create_proj.text
    project_id = create_proj.json()["project"]["id"]

    statuses = client.get(f"/api/v1/projects/{project_id}/statuses", headers=headers)
    assert statuses.status_code == 200, statuses.text
    status_id = statuses.json()["items"][0]["id"]

    create_issue = client.post(
        f"/api/v1/projects/{project_id}/issues",
        headers=headers,
        json={"type": "task", "title": "Worklogs Issue", "status_id": status_id},
    )
    assert create_issue.status_code == 201, create_issue.text
    issue_id = create_issue.json()["issue"]["id"]
    return project_id, issue_id


def _assert_error_response(resp, expected_status: int, expected_code: str):
    assert resp.status_code == expected_status, resp.text
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == expected_code
    assert "message" in data["error"]


@allure.epic("Worklogs")
@allure.feature("Worklog API")
class TestWorklogs:
    @allure.story("Routing/Auth")
    @allure.title("Worklogs endpoints require valid Bearer token")
    def test_routes_are_connected_and_auth_guard_works(self, client, auth_headers):
        _, issue_id = _create_project_and_issue(client, auth_headers)

        no_token = client.get(f"/api/v1/issues/{issue_id}/worklogs")
        _assert_error_response(no_token, 401, "UNAUTHORIZED")

        invalid_token = client.get(
            f"/api/v1/issues/{issue_id}/worklogs",
            headers={"Authorization": "Bearer invalid-token"},
        )
        _assert_error_response(invalid_token, 401, "UNAUTHORIZED")

    @allure.story("Create")
    @allure.title("POST /issues/{id}/worklogs creates worklog and validates payload")
    def test_create_worklog_and_validation_errors(self, client, auth_headers):
        _, issue_id = _create_project_and_issue(client, auth_headers)

        created = client.post(
            f"/api/v1/issues/{issue_id}/worklogs",
            headers=auth_headers,
            json={"work_date": "2026-01-10", "hours": 2.5, "comment": "Initial log"},
        )
        assert created.status_code == 201, created.text
        body = created.json()["worklog"]
        assert body["issue_id"] == issue_id
        assert body["hours"] == pytest.approx(2.5)
        assert "created_at" not in body
        assert "updated_at" not in body

        invalid_hours = client.post(
            f"/api/v1/issues/{issue_id}/worklogs",
            headers=auth_headers,
            json={"work_date": "2026-01-10", "hours": 0},
        )
        _assert_error_response(invalid_hours, 400, "VALIDATION_ERROR")

        invalid_date = client.post(
            f"/api/v1/issues/{issue_id}/worklogs",
            headers=auth_headers,
            json={"work_date": "2026-13-99", "hours": 1},
        )
        _assert_error_response(invalid_date, 400, "VALIDATION_ERROR")

    @allure.story("List by Issue")
    @allure.title("GET /issues/{id}/worklogs supports filters, pagination and summary")
    def test_issue_worklogs_filters_pagination_and_summary(self, client, auth_headers):
        _, issue_id = _create_project_and_issue(client, auth_headers)

        payloads = [
            {"work_date": "2026-01-10", "hours": 1.25},
            {"work_date": "2026-01-11", "hours": 2.50},
            {"work_date": "2026-01-12", "hours": 3.00},
        ]
        for payload in payloads:
            resp = client.post(
                f"/api/v1/issues/{issue_id}/worklogs",
                headers=auth_headers,
                json=payload,
            )
            assert resp.status_code == 201, resp.text

        page_1 = client.get(
            f"/api/v1/issues/{issue_id}/worklogs",
            headers=auth_headers,
            params={"from": "2026-01-11", "to": "2026-01-12", "limit": 1, "offset": 0},
        )
        assert page_1.status_code == 200, page_1.text
        data_1 = page_1.json()
        assert data_1["total"] == 2
        assert len(data_1["items"]) == 1
        assert data_1["items"][0]["work_date"] == "2026-01-12"
        assert data_1["summary"]["logged_hours"] == pytest.approx(5.5)

        page_2 = client.get(
            f"/api/v1/issues/{issue_id}/worklogs",
            headers=auth_headers,
            params={"from": "2026-01-11", "to": "2026-01-12", "limit": 1, "offset": 1},
        )
        assert page_2.status_code == 200, page_2.text
        data_2 = page_2.json()
        assert len(data_2["items"]) == 1
        assert data_2["items"][0]["work_date"] == "2026-01-11"
        assert data_2["summary"]["logged_hours"] == pytest.approx(5.5)

        invalid_period = client.get(
            f"/api/v1/issues/{issue_id}/worklogs",
            headers=auth_headers,
            params={"from": "2026-01-12", "to": "2026-01-11"},
        )
        _assert_error_response(invalid_period, 400, "BAD_REQUEST")

    @allure.story("List by User")
    @allure.title("GET /users/{id}/worklogs enforces access and supports empty result")
    def test_user_worklogs_access_rules_filters_and_empty_result(self, client, auth_headers):
        project_id, issue_id = _create_project_and_issue(client, auth_headers)
        member_headers, member_id = _register_and_login(client, "Member User")
        outsider_headers, _ = _register_and_login(client, "Outsider User")

        add_member = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=auth_headers,
            json={"user_id": member_id, "role": "user"},
        )
        assert add_member.status_code == 201, add_member.text

        for payload in [
            {"work_date": "2026-02-01", "hours": 4},
            {"work_date": "2026-02-02", "hours": 5},
        ]:
            created = client.post(
                f"/api/v1/issues/{issue_id}/worklogs",
                headers=member_headers,
                json=payload,
            )
            assert created.status_code == 201, created.text

        owner_view = client.get(
            f"/api/v1/users/{member_id}/worklogs",
            headers=auth_headers,
            params={"project_id": project_id},
        )
        assert owner_view.status_code == 200, owner_view.text
        assert owner_view.json()["total"] == 2

        outsider_view = client.get(f"/api/v1/users/{member_id}/worklogs", headers=outsider_headers)
        _assert_error_response(outsider_view, 403, "FORBIDDEN")

        empty = client.get(
            f"/api/v1/users/{member_id}/worklogs",
            headers=auth_headers,
            params={"from": "2030-01-01", "to": "2030-01-02"},
        )
        assert empty.status_code == 200, empty.text
        assert empty.json()["items"] == []
        assert empty.json()["total"] == 0

    @allure.story("Update/Delete")
    @allure.title("PATCH/DELETE /worklogs/{id} enforce permissions and not-found behavior")
    def test_patch_delete_forbidden_and_not_found(self, client, auth_headers):
        project_id, issue_id = _create_project_and_issue(client, auth_headers)
        member_headers, member_id = _register_and_login(client, "Patch Member")
        outsider_headers, _ = _register_and_login(client, "Patch Outsider")

        add_member = client.post(
            f"/api/v1/projects/{project_id}/users",
            headers=auth_headers,
            json={"user_id": member_id, "role": "user"},
        )
        assert add_member.status_code == 201, add_member.text

        created = client.post(
            f"/api/v1/issues/{issue_id}/worklogs",
            headers=member_headers,
            json={"work_date": "2026-02-10", "hours": 3},
        )
        assert created.status_code == 201, created.text
        worklog_id = created.json()["worklog"]["id"]

        forbidden = client.patch(
            f"/api/v1/worklogs/{worklog_id}",
            headers=outsider_headers,
            json={"hours": 5},
        )
        _assert_error_response(forbidden, 403, "FORBIDDEN")

        invalid = client.patch(
            f"/api/v1/worklogs/{worklog_id}",
            headers=member_headers,
            json={"hours": 0},
        )
        _assert_error_response(invalid, 400, "VALIDATION_ERROR")

        empty_patch = client.patch(
            f"/api/v1/worklogs/{worklog_id}",
            headers=member_headers,
            json={},
        )
        _assert_error_response(empty_patch, 400, "BAD_REQUEST")

        updated = client.patch(
            f"/api/v1/worklogs/{worklog_id}",
            headers=auth_headers,
            json={"hours": 6.5, "comment": "Updated by owner"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["worklog"]["hours"] == pytest.approx(6.5)
        assert updated.json()["worklog"]["comment"] == "Updated by owner"

        deleted = client.delete(f"/api/v1/worklogs/{worklog_id}", headers=auth_headers)
        assert deleted.status_code == 204, deleted.text

        deleted_again = client.delete(f"/api/v1/worklogs/{worklog_id}", headers=auth_headers)
        _assert_error_response(deleted_again, 404, "NOT_FOUND")

    @allure.story("Create")
    @allure.title("POST /issues/{id}/worklogs returns 403/404 for inaccessible or missing issue")
    def test_create_worklog_for_inaccessible_issue(self, client, auth_headers):
        _, issue_id = _create_project_and_issue(client, auth_headers)
        outsider_headers, _ = _register_and_login(client, "No Access User")

        forbidden = client.post(
            f"/api/v1/issues/{issue_id}/worklogs",
            headers=outsider_headers,
            json={"work_date": "2026-03-01", "hours": 2},
        )
        _assert_error_response(forbidden, 403, "FORBIDDEN")

        unknown_issue = client.post(
            "/api/v1/issues/00000000-0000-0000-0000-000000000000/worklogs",
            headers=auth_headers,
            json={"work_date": "2026-03-01", "hours": 2},
        )
        _assert_error_response(unknown_issue, 404, "NOT_FOUND")
