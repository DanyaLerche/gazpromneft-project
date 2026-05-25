#
# API-интеграционные тесты для эндпоинта for-me.
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import allure

from conftest import _unique_project_key


@allure.epic("ForMe")
@allure.feature("Мои задачи")
class TestForMe:
    @allure.story("Агрегированная выдача")
    @allure.title("GET /for-me возвращает issues, projects, total, filters")
    def test_for_me_returns_aggregated_payload(self, client, auth_headers):
        key = _unique_project_key()
        create_proj = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "ForMe Project"},
        )
        assert create_proj.status_code == 201, create_proj.text
        project_id = create_proj.json()["project"]["id"]

        statuses_resp = client.get(
            f"/api/v1/projects/{project_id}/statuses",
            headers=auth_headers,
        )
        assert statuses_resp.status_code == 200, statuses_resp.text
        status_id = statuses_resp.json()["items"][0]["id"]

        create_issue = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            json={"type": "task", "title": "For me issue", "status_id": status_id},
        )
        assert create_issue.status_code == 201, create_issue.text

        resp = client.get("/api/v1/for-me", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert "issues" in data
        assert "projects" in data
        assert "total" in data
        assert "filters" in data
        assert "mini_digest" in data
        assert "action_history" in data
        assert "statuses" in data["filters"]
        assert "users" in data["filters"]
        assert any(item["id"] == project_id for item in data["projects"])

    @allure.story("Трудозатраты в дашборде")
    @allure.title("GET /for-me возвращает logged_hours для задач с worklog из календаря")
    def test_for_me_returns_logged_hours_for_issues(self, client, auth_headers):
        key = _unique_project_key()
        create_proj = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "ForMe Worklog Project"},
        )
        assert create_proj.status_code == 201, create_proj.text
        project_id = create_proj.json()["project"]["id"]

        statuses_resp = client.get(
            f"/api/v1/projects/{project_id}/statuses",
            headers=auth_headers,
        )
        assert statuses_resp.status_code == 200, statuses_resp.text
        status_id = statuses_resp.json()["items"][0]["id"]

        create_issue = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            json={"type": "task", "title": "Worklog issue", "status_id": status_id},
        )
        assert create_issue.status_code == 201, create_issue.text
        issue_id = create_issue.json()["issue"]["id"]

        create_worklog = client.post(
            f"/api/v1/issues/{issue_id}/worklogs",
            headers=auth_headers,
            json={"work_date": "2026-04-22", "hours": 2.5, "comment": "Calendar actual"},
        )
        assert create_worklog.status_code == 201, create_worklog.text

        resp = client.get("/api/v1/for-me", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()

        issue = next(item for item in data["issues"] if item["id"] == issue_id)
        assert issue["logged_hours"] == 2.5

    @allure.story("Мини-дайджест и авто-история")
    @allure.title("GET /for-me возвращает изменения после last_seen_timestamp и 5 последних действий")
    def test_for_me_returns_digest_and_action_history(self, client, auth_headers):
        key = _unique_project_key()
        create_proj = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "ForMe Digest Project"},
        )
        assert create_proj.status_code == 201, create_proj.text
        project_id = create_proj.json()["project"]["id"]

        statuses_resp = client.get(
            f"/api/v1/projects/{project_id}/statuses",
            headers=auth_headers,
        )
        assert statuses_resp.status_code == 200, statuses_resp.text
        status_id = statuses_resp.json()["items"][0]["id"]

        last_seen_timestamp = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
        create_issue = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            json={"type": "task", "title": "Digest issue", "status_id": status_id},
        )
        assert create_issue.status_code == 201, create_issue.text
        issue_id = create_issue.json()["issue"]["id"]

        digest_resp = client.get(
            "/api/v1/for-me",
            headers=auth_headers,
            params={"last_seen_timestamp": last_seen_timestamp},
        )
        assert digest_resp.status_code == 200, digest_resp.text
        data = digest_resp.json()

        assert data["mini_digest"]["last_seen_timestamp"] is not None
        assert len(data["mini_digest"]["items"]) <= 5
        assert any(item["issue_id"] == issue_id for item in data["mini_digest"]["items"])

        assert len(data["action_history"]["items"]) <= 5
        assert any(
            item["issue_id"] == issue_id and item["action_type"] == "issue_created"
            for item in data["action_history"]["items"]
        )
