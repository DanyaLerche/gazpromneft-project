#
# Contract-тесты: проверка соответствия ответов API OpenAPI-спецификации.
#
# Гарантирует, что реализованные эндпоинты возвращают структуры данных
# в соответствии с контрактом. Остаётся актуальным при добавлении новых
# эндпоинтов из openapi-v0.1.0.yaml — добавляются только новые case.
from __future__ import annotations

import os

import allure

# Требуемые поля в успешных ответах по OpenAPI (components.schemas)
LOGIN_RESPONSE_REQUIRED = {"access_token", "refresh_token", "user"}
USER_REQUIRED = {"id", "email", "full_name", "is_active", "app_role", "created_at"}
REGISTER_RESPONSE_REQUIRED = {"user"}
ME_RESPONSE_REQUIRED = {"user"}
PROJECT_REQUIRED = {
    "id",
    "key",
    "name",
    "description",
    "category",
    "created_by",
    "created_at",
    "updated_at",
    "current_user_role",
}
PAGED_PROJECTS_REQUIRED = {"items", "total"}
PROJECT_USER_REQUIRED = {"project_id", "user_id", "role"}
PAGED_PROJECT_USERS_REQUIRED = {"items", "total"}
PAGED_USERS_REQUIRED = {"items", "total"}
PAGED_ISSUES_REQUIRED = {"items", "total"}
ISSUE_REQUIRED = {
    "id", "project_id", "key", "type", "title", "status_id",
    "author_id", "created_at", "updated_at",
}
ISSUE_RESPONSE_REQUIRED = {"issue"}
ISSUE_DETAILS_RESPONSE_REQUIRED = {"issue", "watchers", "comments", "attachments", "worklog_summary"}
NEW_EMPLOYEE_EPIC_TITLE = "Режим «Новый сотрудник»: авто-onboarding (MVP)"
NEW_EMPLOYEE_EPIC_DESCRIPTION = (
    "Система автоматически рекомендует: что читать (Wiki), какие задачи посмотреть (Issues), "
    "кто ключевые люди (Users). Только на основе данных проекта (активность, связи, роли), "
    "без вручную написанных гайдов."
)
ONBOARDING_SIGNALS_TASK_TITLE = "Спроектировать сигналы из реальных данных (что считаем важным)"
STATUS_LIST_REQUIRED = {"items"}
STATUS_RESPONSE_REQUIRED = {"status"}
STATUS_REQUIRED = {"id", "project_id", "name", "category", "sort_order"}
CRITICALITY_LIST_REQUIRED = {"items"}
CRITICALITY_REQUIRED = {"id", "name", "level"}
FOR_ME_REQUIRED = {"issues", "projects", "total", "filters", "mini_digest", "action_history"}
FOR_ME_FILTERS_REQUIRED = {"statuses", "users"}
FOR_ME_MINI_DIGEST_REQUIRED = {"last_seen_timestamp", "generated_at", "items"}
FOR_ME_ACTION_HISTORY_REQUIRED = {"items"}
WIKI_PAGE_REQUIRED = {
    "id",
    "project_id",
    "parent_id",
    "title",
    "content_md",
    "rendered_html",
    "version",
    "created_by",
    "updated_by",
    "created_at",
    "updated_at",
}
WIKI_TREE_ITEM_REQUIRED = {"id", "project_id", "parent_id", "title", "version", "updated_at", "children"}
WIKI_REVISION_REQUIRED = {
    "id",
    "page_id",
    "project_id",
    "parent_id",
    "version",
    "title",
    "content_md",
    "rendered_html",
    "created_by",
    "created_at",
}
WIKI_ATTACHMENT_REQUIRED = {
    "id",
    "page_id",
    "uploaded_by",
    "file_name",
    "mime_type",
    "size_bytes",
    "storage_key",
    "created_at",
}
WIKI_UPLOAD_REQUIRED = {"storage_key", "upload_url", "headers", "fields", "method", "expires_in"}
ONBOARDING_RECOMMENDATIONS_REQUIRED = {"reads", "issues_to_review", "key_people", "generated_at", "cached"}
PROJECT_ONBOARDING_PREFERENCES_REQUIRED = {"preferences"}
PROJECT_ONBOARDING_PREFERENCES_PAYLOAD_REQUIRED = {"new_employee_mode"}
PROJECT_ONBOARDING_ASSIGNEES_REQUIRED = {"assignees"}
ONBOARDING_ASSIGNEE_ITEM_REQUIRED = {"user_id", "full_name"}


def _has_required(data: dict, required: set, path: str = "") -> list[str]:
    """Возвращает список отсутствующих обязательных полей."""
    if not isinstance(data, dict):
        return [f"{path}: expected object"]
    missing = []
    for key in required:
        if key not in data:
            missing.append(f"{path}.{key}" if path else key)
    return missing


@allure.epic("Contract")
@allure.feature("OpenAPI")
class TestOpenAPIContract:
    """Соответствие ответов API OpenAPI-спецификации."""

    @allure.story("Auth")
    @allure.title("LoginResponse: access_token, refresh_token, user")
    def test_login_response_contract(self, client):
        with allure.step("POST /auth/login"):
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": "demo.user@example.com", "password": "demo12345"},
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        missing = _has_required(data, LOGIN_RESPONSE_REQUIRED)
        assert not missing, f"Missing: {missing}"
        missing_user = _has_required(data["user"], USER_REQUIRED, "user")
        assert not missing_user, f"user missing: {missing_user}"

    @allure.story("Auth")
    @allure.title("RegisterResponse: user")
    def test_register_response_contract(self, client):
        email = f"contract-{os.urandom(4).hex()}@example.com"
        with allure.step("POST /auth/register"):
            resp = client.post(
                "/api/v1/auth/register",
                json={"email": email, "full_name": "Contract User", "password": "password123"},
            )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        missing = _has_required(data, REGISTER_RESPONSE_REQUIRED)
        assert not missing, f"Missing: {missing}"
        missing_user = _has_required(data["user"], USER_REQUIRED, "user")
        assert not missing_user, f"user missing: {missing_user}"

    @allure.story("Auth")
    @allure.title("MeResponse: user")
    def test_me_response_contract(self, client, auth_headers):
        with allure.step("GET /me"):
            resp = client.get("/api/v1/me", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        missing = _has_required(data, ME_RESPONSE_REQUIRED)
        assert not missing, f"Missing: {missing}"
        missing_user = _has_required(data["user"], USER_REQUIRED, "user")
        assert not missing_user, f"user missing: {missing_user}"

    @allure.story("Projects")
    @allure.title("PagedProjects: items, total")
    def test_list_projects_contract(self, client, auth_headers):
        with allure.step("GET /projects"):
            resp = client.get("/api/v1/projects", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        missing = _has_required(data, PAGED_PROJECTS_REQUIRED)
        assert not missing, f"Missing: {missing}"
        for item in data.get("items", []):
            missing_p = _has_required(item, PROJECT_REQUIRED, "items[]")
            assert not missing_p, f"Project missing: {missing_p}"

    @allure.story("Projects")
    @allure.title("ProjectResponseWrapper: project")
    def test_create_project_contract(self, client, auth_headers):
        from conftest import _unique_project_key
        key = _unique_project_key()
        with allure.step("POST /projects"):
            resp = client.post(
                "/api/v1/projects",
                headers=auth_headers,
                json={"key": key, "name": "Contract Proj"},
            )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "project" in data, "Missing project"
        missing = _has_required(data["project"], PROJECT_REQUIRED, "project")
        assert not missing, f"project missing: {missing}"

    @allure.story("Projects")
    @allure.title("OpenAPI includes onboarding recommendations endpoint and schema")
    def test_onboarding_recommendations_openapi_contract(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        path = "/api/v1/projects/{project_id}/onboarding/recommendations"
        assert path in data["paths"]
        endpoint = data["paths"][path]["get"]
        schema_ref = endpoint["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        assert schema_ref.endswith("/OnboardingRecommendationsResponse")
        force_query_param = next((p for p in endpoint["parameters"] if p["name"] == "force"), None)
        assert force_query_param is not None
        assert force_query_param["schema"]["type"] == "boolean"

        onboarding_schema = data["components"]["schemas"]["OnboardingRecommendationsResponse"]
        missing = _has_required(onboarding_schema["properties"], ONBOARDING_RECOMMENDATIONS_REQUIRED)
        assert not missing, f"Onboarding schema missing fields: {missing}"
        assert "email" in data["components"]["schemas"]["OnboardingKeyPersonItem"]["properties"]

    @allure.story("Projects")
    @allure.title("OpenAPI includes project onboarding preferences endpoints and schema")
    def test_project_preferences_openapi_contract(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        path = "/api/v1/projects/{project_id}/me/preferences"
        assert path in data["paths"]
        assert "get" in data["paths"][path]
        assert "patch" in data["paths"][path]

        patch_body = data["paths"][path]["patch"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        assert patch_body.endswith("/UpdateProjectOnboardingPreferencesRequest")

        response_schema = data["components"]["schemas"]["ProjectOnboardingPreferencesResponse"]
        missing = _has_required(response_schema["properties"], PROJECT_ONBOARDING_PREFERENCES_REQUIRED)
        assert not missing, f"Project preferences schema missing fields: {missing}"

        payload_schema = data["components"]["schemas"]["ProjectOnboardingPreferences"]["properties"]
        missing_payload = _has_required(payload_schema, PROJECT_ONBOARDING_PREFERENCES_PAYLOAD_REQUIRED)
        assert not missing_payload, f"Project preferences payload missing fields: {missing_payload}"

    @allure.story("Projects")
    @allure.title("OpenAPI includes onboarding assignees endpoints and schema")
    def test_project_onboarding_assignees_openapi_contract(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        path = "/api/v1/projects/{project_id}/onboarding/assignees"
        assert path in data["paths"]
        assert "get" in data["paths"][path]
        assert "patch" in data["paths"][path]

        patch_body = data["paths"][path]["patch"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        assert patch_body.endswith("/UpdateProjectOnboardingAssigneesRequest")

        response_schema = data["components"]["schemas"]["ProjectOnboardingAssigneesResponse"]
        missing = _has_required(response_schema["properties"], PROJECT_ONBOARDING_ASSIGNEES_REQUIRED)
        assert not missing, f"Project onboarding assignees schema missing fields: {missing}"

        assignee_schema = data["components"]["schemas"]["OnboardingAssigneeItem"]["properties"]
        missing_assignee = _has_required(assignee_schema, ONBOARDING_ASSIGNEE_ITEM_REQUIRED)
        assert not missing_assignee, f"Onboarding assignee item schema missing fields: {missing_assignee}"

    @allure.story("OpenAPI")
    @allure.title("OpenAPI includes RBAC schemas for platform and project user management")
    def test_rbac_openapi_contract(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        user_schema = data["components"]["schemas"]["User"]
        user_props = user_schema["properties"]
        assert "app_role" in user_props
        assert "app_role" in user_schema["required"]
        assert data["components"]["schemas"]["AppRole"]["enum"] == ["user", "admin_app"]

        project_schema = data["components"]["schemas"]["ProjectResponse"]
        project_props = project_schema["properties"]
        assert "current_user_role" in project_props
        for field_name in ("description", "category", "updated_at", "current_user_role"):
            assert field_name in project_props
        for field_name in ("updated_at", "current_user_role"):
            assert field_name in project_schema["required"]

        assert data["components"]["schemas"]["ProjectRole"]["enum"] == ["user", "admin_project"]

        update_project = data["paths"]["/api/v1/projects/{project_id}"]["patch"]
        assert "requestBody" in update_project
        update_project_schema = update_project["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        assert update_project_schema.endswith("/UpdateProjectRequest")

        project_users_path = data["paths"]["/api/v1/projects/{project_id}/users"]
        assert "get" in project_users_path
        assert "post" in project_users_path

        reports_path = data["paths"]["/api/v1/projects/{project_id}/reports/dashboard"]
        assert "get" in reports_path
        report_get = reports_path["get"]
        assert report_get["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
            "/ProjectDashboardReportResponse"
        )
        reports_export_path = data["paths"]["/api/v1/projects/{project_id}/reports/dashboard/export"]
        assert "get" in reports_export_path
        export_get = reports_export_path["get"]
        export_param_names = {item["name"] for item in export_get.get("parameters", [])}
        assert {"recent_days", "overdue_limit", "format"}.issubset(export_param_names)
        assert "200" in export_get["responses"]

        update_project_user = data["paths"]["/api/v1/projects/{project_id}/users/{user_id}"]["patch"]
        assert "requestBody" in update_project_user
        update_project_user_schema = update_project_user["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        assert update_project_user_schema.endswith("/UpdateProjectUserRequest")
        assert "delete" in data["paths"]["/api/v1/projects/{project_id}/users/{user_id}"]

        assert "/api/v1/projects/{project_id}/users/search" in data["paths"]

        platform_users_path = data["paths"]["/api/v1/users"]
        assert "get" in platform_users_path

        update_platform_user = data["paths"]["/api/v1/users/{user_id}"]["patch"]
        assert "requestBody" in update_platform_user
        update_platform_user_schema = update_platform_user["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        assert update_platform_user_schema.endswith("/UpdateUserAppRoleRequest")

        update_user_app_role_schema = data["components"]["schemas"]["UpdateUserAppRoleRequest"]
        assert "app_role" in update_user_app_role_schema["properties"]
        assert "app_role" in update_user_app_role_schema["required"]

    @allure.story("Users")
    @allure.title("PagedUsers contract for platform user management")
    def test_list_platform_users_contract(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "demo.user@example.com", "password": "demo12345"},
        )
        assert resp.status_code == 200, resp.text
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

        listed = client.get("/api/v1/users", headers=headers, params={"limit": 10, "offset": 0})
        assert listed.status_code == 200, listed.text
        data = listed.json()
        missing = _has_required(data, PAGED_USERS_REQUIRED)
        assert not missing, f"Missing: {missing}"
        for item in data.get("items", []):
            missing_user = _has_required(item, USER_REQUIRED, "items[]")
            assert not missing_user, f"User missing: {missing_user}"

    @allure.story("Issues")
    @allure.title("PagedIssues: items, total")
    def test_list_issues_contract(self, client, auth_headers):
        from conftest import _unique_project_key
        key = _unique_project_key()
        create = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "P"},
        )
        project_id = create.json()["project"]["id"]
        statuses = client.get(
            f"/api/v1/projects/{project_id}/statuses",
            headers=auth_headers,
        )
        status_id = statuses.json()["items"][0]["id"]
        client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            json={"type": "task", "title": "I", "status_id": status_id},
        )
        with allure.step("GET /projects/{id}/issues"):
            resp = client.get(
                f"/api/v1/projects/{project_id}/issues",
                headers=auth_headers,
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        missing = _has_required(data, PAGED_ISSUES_REQUIRED)
        assert not missing, f"Missing: {missing}"
        for item in data.get("items", []):
            missing_i = _has_required(item, ISSUE_REQUIRED, "items[]")
            assert not missing_i, f"Issue missing: {missing_i}"

    @allure.story("Issues")
    @allure.title("OpenAPI includes epic example for MVP onboarding issue creation")
    def test_create_epic_openapi_example_contract(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        create_issue = data["paths"]["/api/v1/projects/{project_id}/issues"]["post"]
        request_body = create_issue["requestBody"]["content"]["application/json"]
        assert request_body["schema"]["$ref"].endswith("/CreateIssueRequest")

        examples = request_body["examples"]
        assert "newEmployeeOnboardingMvpEpic" in examples
        epic_example = examples["newEmployeeOnboardingMvpEpic"]["value"]

        assert epic_example["type"] == "epic"
        assert epic_example["title"] == NEW_EMPLOYEE_EPIC_TITLE
        assert epic_example["description"] == NEW_EMPLOYEE_EPIC_DESCRIPTION
        assert "status_id" in epic_example

        assert "designOnboardingSignalsTask" in examples
        task_example = examples["designOnboardingSignalsTask"]["value"]
        assert task_example["type"] == "task"
        assert task_example["title"] == ONBOARDING_SIGNALS_TASK_TITLE
        assert "parent_id" in task_example
        assert "backend/docs/onboarding_signals.md" in task_example["description"]

    @allure.story("Statuses")
    @allure.title("StatusListResponse: items with Status")
    def test_list_statuses_contract(self, client, auth_headers):
        from conftest import _unique_project_key
        key = _unique_project_key()
        create = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "P"},
        )
        project_id = create.json()["project"]["id"]
        with allure.step("GET /projects/{id}/statuses"):
            resp = client.get(
                f"/api/v1/projects/{project_id}/statuses",
                headers=auth_headers,
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        missing = _has_required(data, STATUS_LIST_REQUIRED)
        assert not missing, f"Missing: {missing}"
        for item in data.get("items", []):
            missing_s = _has_required(item, STATUS_REQUIRED, "items[]")
            assert not missing_s, f"Status missing: {missing_s}"

    @allure.story("Criticalities")
    @allure.title("CriticalityListResponse: items with Criticality")
    def test_list_criticalities_contract(self, client, auth_headers):
        with allure.step("GET /criticalities"):
            resp = client.get("/api/v1/criticalities", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        missing = _has_required(data, CRITICALITY_LIST_REQUIRED)
        assert not missing, f"Missing: {missing}"
        for item in data.get("items", []):
            missing_c = _has_required(item, CRITICALITY_REQUIRED, "items[]")
            assert not missing_c, f"Criticality missing: {missing_c}"

    @allure.story("ForMe")
    @allure.title("ForMeResponse: issues, projects, total, filters")
    def test_for_me_contract(self, client, auth_headers):
        from conftest import _unique_project_key

        key = _unique_project_key()
        create = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "ForMe Contract"},
        )
        assert create.status_code == 201, create.text
        project_id = create.json()["project"]["id"]

        statuses = client.get(
            f"/api/v1/projects/{project_id}/statuses",
            headers=auth_headers,
        )
        assert statuses.status_code == 200, statuses.text
        status_id = statuses.json()["items"][0]["id"]

        issue = client.post(
            f"/api/v1/projects/{project_id}/issues",
            headers=auth_headers,
            json={"type": "task", "title": "Contract ForMe", "status_id": status_id},
        )
        assert issue.status_code == 201, issue.text

        resp = client.get("/api/v1/for-me", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()

        missing = _has_required(data, FOR_ME_REQUIRED)
        assert not missing, f"Missing: {missing}"
        missing_filters = _has_required(data["filters"], FOR_ME_FILTERS_REQUIRED, "filters")
        assert not missing_filters, f"filters missing: {missing_filters}"
        missing_digest = _has_required(data["mini_digest"], FOR_ME_MINI_DIGEST_REQUIRED, "mini_digest")
        assert not missing_digest, f"mini_digest missing: {missing_digest}"
        missing_action_history = _has_required(
            data["action_history"], FOR_ME_ACTION_HISTORY_REQUIRED, "action_history"
        )
        assert not missing_action_history, f"action_history missing: {missing_action_history}"

    @allure.story("Wiki")
    @allure.title("Wiki pages and render responses contract")
    def test_wiki_pages_contract(self, client, auth_headers):
        from conftest import _unique_project_key

        key = _unique_project_key()
        create = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Wiki Contract"},
        )
        assert create.status_code == 201, create.text
        project_id = create.json()["project"]["id"]

        created = client.post(
            f"/api/v1/projects/{project_id}/wiki/pages",
            headers=auth_headers,
            json={"title": "Main", "content_md": "# Main"},
        )
        assert created.status_code == 201, created.text
        data = created.json()
        assert "page" in data
        missing_page = _has_required(data["page"], WIKI_PAGE_REQUIRED, "page")
        assert not missing_page, f"page missing: {missing_page}"
        page_id = data["page"]["id"]

        listed = client.get(f"/api/v1/projects/{project_id}/wiki/pages", headers=auth_headers)
        assert listed.status_code == 200, listed.text
        assert "items" in listed.json()
        if listed.json()["items"]:
            missing_tree = _has_required(listed.json()["items"][0], WIKI_TREE_ITEM_REQUIRED, "items[]")
            assert not missing_tree, f"tree item missing: {missing_tree}"

        fetched = client.get(f"/api/v1/projects/{project_id}/wiki/pages/{page_id}", headers=auth_headers)
        assert fetched.status_code == 200, fetched.text
        missing_fetched = _has_required(fetched.json()["page"], WIKI_PAGE_REQUIRED, "page")
        assert not missing_fetched, f"fetched page missing: {missing_fetched}"

        rendered = client.post(
            f"/api/v1/projects/{project_id}/wiki/render",
            headers=auth_headers,
            json={"content_md": "{info}ok{info}"},
        )
        assert rendered.status_code == 200, rendered.text
        assert "rendered_html" in rendered.json()

    @allure.story("Wiki")
    @allure.title("Wiki revisions and attachments responses contract")
    def test_wiki_revisions_attachments_contract(self, client, auth_headers, monkeypatch):
        from conftest import _unique_project_key
        from backend.services import wiki_service

        state = {"objects": set()}

        class FakeS3Client:
            async def generate_presigned_post(self, Bucket, Key, Fields=None, Conditions=None, ExpiresIn=900):
                return {"url": "http://fake-s3.local/upload", "fields": {"key": Key}}

            async def head_object(self, Bucket, Key):
                if Key not in state["objects"]:
                    raise RuntimeError("not found")
                return {"Key": Key}

            async def generate_presigned_url(self, ClientMethod, Params, ExpiresIn=900):
                return f"http://fake-s3.local/download/{Params['Key']}"

            async def delete_object(self, Bucket, Key):
                state["objects"].discard(Key)
                return {"DeleteMarker": True}

        class FakeS3Context:
            async def __aenter__(self):
                return FakeS3Client()

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class FakeSession:
            def client(self, *args, **kwargs):
                return FakeS3Context()

        monkeypatch.setattr(wiki_service.aioboto3, "Session", lambda: FakeSession())

        key = _unique_project_key()
        create = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"key": key, "name": "Wiki Files Contract"},
        )
        project_id = create.json()["project"]["id"]

        page = client.post(
            f"/api/v1/projects/{project_id}/wiki/pages",
            headers=auth_headers,
            json={"title": "History", "content_md": "v1"},
        )
        page_id = page.json()["page"]["id"]

        client.patch(
            f"/api/v1/projects/{project_id}/wiki/pages/{page_id}",
            headers=auth_headers,
            json={"content_md": "v2"},
        )

        revisions = client.get(
            f"/api/v1/projects/{project_id}/wiki/pages/{page_id}/revisions",
            headers=auth_headers,
        )
        assert revisions.status_code == 200, revisions.text
        if revisions.json()["items"]:
            missing_revision = _has_required(revisions.json()["items"][0], WIKI_REVISION_REQUIRED, "items[]")
            assert not missing_revision, f"revision missing: {missing_revision}"

        restored = client.post(
            f"/api/v1/projects/{project_id}/wiki/pages/{page_id}/restore",
            headers=auth_headers,
            json={"version": 1},
        )
        assert restored.status_code == 200, restored.text
        missing_restored = _has_required(restored.json()["page"], WIKI_PAGE_REQUIRED, "page")
        assert not missing_restored, f"restored page missing: {missing_restored}"

        prepare = client.post(
            f"/api/v1/projects/{project_id}/wiki/pages/{page_id}/attachments/prepare",
            headers=auth_headers,
            json={"file_name": "manual.pdf", "mime_type": "application/pdf", "size_bytes": 22_000_000},
        )
        assert prepare.status_code == 200, prepare.text
        missing_upload = _has_required(prepare.json()["upload"], WIKI_UPLOAD_REQUIRED, "upload")
        assert not missing_upload, f"upload missing: {missing_upload}"
        storage_key = prepare.json()["upload"]["storage_key"]
        state["objects"].add(storage_key)

        created_attachment = client.post(
            f"/api/v1/projects/{project_id}/wiki/pages/{page_id}/attachments",
            headers=auth_headers,
            json={
                "storage_key": storage_key,
                "file_name": "manual.pdf",
                "mime_type": "application/pdf",
                "size_bytes": 22_000_000,
            },
        )
        assert created_attachment.status_code == 201, created_attachment.text
        missing_attachment = _has_required(
            created_attachment.json()["attachment"], WIKI_ATTACHMENT_REQUIRED, "attachment"
        )
        assert not missing_attachment, f"attachment missing: {missing_attachment}"
