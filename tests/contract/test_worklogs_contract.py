from __future__ import annotations

import allure

from conftest import _unique_project_key

WORKLOG_REQUIRED = {"id", "issue_id", "user_id", "work_date", "hours", "comment"}
PAGED_WORKLOGS_REQUIRED = {"items", "total"}
PAGED_WORKLOGS_WITH_SUMMARY_REQUIRED = {"items", "total", "summary"}
WORKLOG_SUMMARY_REQUIRED = {"planned_hours", "logged_hours"}
ERROR_REQUIRED = {"code", "message"}


def _has_required(data: dict, required: set, path: str = "") -> list[str]:
    if not isinstance(data, dict):
        return [f"{path}: expected object"]
    missing = []
    for key in required:
        if key not in data:
            missing.append(f"{path}.{key}" if path else key)
    return missing


def _create_project_issue_and_worklog(client, headers: dict[str, str]) -> tuple[str, str, str]:
    key = _unique_project_key()
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"key": key, "name": "Contract Worklogs"},
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["project"]["id"]

    statuses = client.get(f"/api/v1/projects/{project_id}/statuses", headers=headers)
    assert statuses.status_code == 200, statuses.text
    status_id = statuses.json()["items"][0]["id"]

    issue = client.post(
        f"/api/v1/projects/{project_id}/issues",
        headers=headers,
        json={"type": "task", "title": "Contract Worklogs Issue", "status_id": status_id},
    )
    assert issue.status_code == 201, issue.text
    issue_id = issue.json()["issue"]["id"]

    worklog = client.post(
        f"/api/v1/issues/{issue_id}/worklogs",
        headers=headers,
        json={"work_date": "2026-03-20", "hours": 3.5, "comment": "Contract"},
    )
    assert worklog.status_code == 201, worklog.text
    worklog_id = worklog.json()["worklog"]["id"]
    return project_id, issue_id, worklog_id


@allure.epic("Contract")
@allure.feature("OpenAPI Worklogs")
class TestWorklogsOpenAPIContract:
    @allure.story("Worklogs")
    @allure.title("CreateWorklogResponse: { worklog }")
    def test_create_worklog_contract(self, client, auth_headers):
        _, issue_id, _ = _create_project_issue_and_worklog(client, auth_headers)

        resp = client.post(
            f"/api/v1/issues/{issue_id}/worklogs",
            headers=auth_headers,
            json={"work_date": "2026-03-21", "hours": 1.25},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "worklog" in data
        missing = _has_required(data["worklog"], WORKLOG_REQUIRED, "worklog")
        assert not missing, f"worklog missing: {missing}"

    @allure.story("Worklogs")
    @allure.title("GET /issues/{issueId}/worklogs: PagedWorklogsWithSummary")
    def test_list_issue_worklogs_contract(self, client, auth_headers):
        _, issue_id, _ = _create_project_issue_and_worklog(client, auth_headers)

        resp = client.get(f"/api/v1/issues/{issue_id}/worklogs", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()

        missing = _has_required(data, PAGED_WORKLOGS_WITH_SUMMARY_REQUIRED)
        assert not missing, f"Missing: {missing}"
        missing_summary = _has_required(data["summary"], WORKLOG_SUMMARY_REQUIRED, "summary")
        assert not missing_summary, f"summary missing: {missing_summary}"
        for item in data.get("items", []):
            missing_item = _has_required(item, WORKLOG_REQUIRED, "items[]")
            assert not missing_item, f"worklog missing: {missing_item}"

    @allure.story("Worklogs")
    @allure.title("GET /users/{userId}/worklogs: PagedWorklogs")
    def test_list_user_worklogs_contract(self, client, auth_headers):
        _, _, _ = _create_project_issue_and_worklog(client, auth_headers)

        me = client.get("/api/v1/me", headers=auth_headers)
        assert me.status_code == 200, me.text
        user_id = me.json()["user"]["id"]

        resp = client.get(f"/api/v1/users/{user_id}/worklogs", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        missing = _has_required(data, PAGED_WORKLOGS_REQUIRED)
        assert not missing, f"Missing: {missing}"
        for item in data.get("items", []):
            missing_item = _has_required(item, WORKLOG_REQUIRED, "items[]")
            assert not missing_item, f"worklog missing: {missing_item}"

    @allure.story("Worklogs")
    @allure.title("PATCH /worklogs/{worklogId}: { worklog }")
    def test_update_worklog_contract(self, client, auth_headers):
        _, _, worklog_id = _create_project_issue_and_worklog(client, auth_headers)

        resp = client.patch(
            f"/api/v1/worklogs/{worklog_id}",
            headers=auth_headers,
            json={"hours": 4.75, "comment": "Updated"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "worklog" in data
        missing = _has_required(data["worklog"], WORKLOG_REQUIRED, "worklog")
        assert not missing, f"worklog missing: {missing}"

    @allure.story("Errors")
    @allure.title("Worklogs errors use ErrorResponse shape")
    def test_worklogs_error_response_contract(self, client):
        resp = client.get("/api/v1/issues/00000000-0000-0000-0000-000000000000/worklogs")
        assert resp.status_code == 401, resp.text
        data = resp.json()
        assert "error" in data
        missing = _has_required(data["error"], ERROR_REQUIRED, "error")
        assert not missing, f"error missing: {missing}"
