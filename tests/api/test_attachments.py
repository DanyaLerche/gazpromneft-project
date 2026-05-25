from __future__ import annotations

import allure
import pytest

from conftest import _unique_email, _unique_project_key
from backend.services import attachments_service


@pytest.fixture
def s3_mock(monkeypatch):
    state = {"objects": set(), "deleted": []}

    class FakeS3Client:
        async def generate_presigned_post(self, Bucket, Key, Fields=None, Conditions=None, ExpiresIn=900):
            return {
                "url": "http://fake-s3.local/upload",
                "fields": {
                    "key": Key,
                    "Content-Type": (Fields or {}).get("Content-Type", "application/octet-stream"),
                },
            }

        async def head_object(self, Bucket, Key):
            if Key not in state["objects"]:
                raise RuntimeError("not found")
            return {"Key": Key}

        async def generate_presigned_url(self, ClientMethod, Params, ExpiresIn=900):
            return f"http://fake-s3.local/download/{Params['Key']}"

        async def delete_object(self, Bucket, Key):
            state["deleted"].append(Key)
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

    monkeypatch.setattr(attachments_service.aioboto3, "Session", lambda: FakeSession())
    return state


def _register_and_login(client, full_name: str) -> tuple[dict[str, str], str]:
    email = _unique_email()
    password = "password123"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": full_name, "password": password},
    )
    assert reg.status_code == 201, reg.text

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    data = login.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]["id"]


def _create_project_and_issue(client, headers: dict[str, str]) -> tuple[str, str]:
    key = _unique_project_key()
    create_proj = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"key": key, "name": "Attachments Project"},
    )
    assert create_proj.status_code == 201, create_proj.text
    project_id = create_proj.json()["project"]["id"]

    statuses = client.get(f"/api/v1/projects/{project_id}/statuses", headers=headers)
    assert statuses.status_code == 200, statuses.text
    status_id = statuses.json()["items"][0]["id"]

    create_issue = client.post(
        f"/api/v1/projects/{project_id}/issues",
        headers=headers,
        json={"type": "task", "title": "Issue with attachment", "status_id": status_id},
    )
    assert create_issue.status_code == 201, create_issue.text
    return project_id, create_issue.json()["issue"]["id"]


def _assert_error(resp, expected_status: int, code: str):
    assert resp.status_code == expected_status, resp.text
    payload = resp.json()
    assert payload["error"]["code"] == code


@allure.epic("Attachments")
@allure.feature("API")
class TestAttachmentsAPI:
    @allure.story("Presigned Upload")
    @allure.title("Подготовка загрузки и подтверждение вложения")
    def test_prepare_and_confirm_attachment(self, client, auth_headers, s3_mock):
        _, issue_id = _create_project_and_issue(client, auth_headers)

        prepare = client.post(
            f"/api/v1/issues/{issue_id}/attachments/prepare",
            headers=auth_headers,
            json={
                "file_name": "spec.pdf",
                "mime_type": "application/pdf",
                "size_bytes": 12345,
            },
        )
        assert prepare.status_code == 200, prepare.text
        upload = prepare.json()["upload"]
        storage_key = upload["storage_key"]
        assert upload["upload_url"].startswith("http://fake-s3.local")
        assert "fields" in upload

        # Эмуляция успешной прямой загрузки на S3 клиентом.
        s3_mock["objects"].add(storage_key)

        confirm = client.post(
            f"/api/v1/issues/{issue_id}/attachments",
            headers=auth_headers,
            json={
                "storage_key": storage_key,
                "file_name": "spec.pdf",
                "mime_type": "application/pdf",
                "size_bytes": 12345,
            },
        )
        assert confirm.status_code == 201, confirm.text
        attachment = confirm.json()["attachment"]
        assert attachment["issue_id"] == issue_id
        assert attachment["storage_key"] == storage_key

    @allure.story("CRUD")
    @allure.title("Список вложений, presigned download и удаление")
    def test_list_download_delete_attachment(self, client, auth_headers, s3_mock):
        _, issue_id = _create_project_and_issue(client, auth_headers)

        prepare = client.post(
            f"/api/v1/issues/{issue_id}/attachments/prepare",
            headers=auth_headers,
            json={
                "file_name": "diagram.png",
                "mime_type": "image/png",
                "size_bytes": 1024,
            },
        )
        storage_key = prepare.json()["upload"]["storage_key"]
        s3_mock["objects"].add(storage_key)

        created = client.post(
            f"/api/v1/issues/{issue_id}/attachments",
            headers=auth_headers,
            json={
                "storage_key": storage_key,
                "file_name": "diagram.png",
                "mime_type": "image/png",
                "size_bytes": 1024,
            },
        )
        assert created.status_code == 201, created.text
        attachment_id = created.json()["attachment"]["id"]

        listed = client.get(f"/api/v1/issues/{issue_id}/attachments", headers=auth_headers)
        assert listed.status_code == 200, listed.text
        assert listed.json()["items"][0]["id"] == attachment_id

        download = client.get(f"/api/v1/attachments/{attachment_id}/download", headers=auth_headers)
        assert download.status_code == 200, download.text
        assert storage_key in download.json()["download_url"]

        deleted = client.delete(f"/api/v1/attachments/{attachment_id}", headers=auth_headers)
        assert deleted.status_code == 204, deleted.text
        assert storage_key in s3_mock["deleted"]

    @allure.story("Access")
    @allure.title("Пользователь без доступа не может работать с вложениями чужой задачи")
    def test_attachment_access_forbidden(self, client, auth_headers):
        _, issue_id = _create_project_and_issue(client, auth_headers)
        outsider_headers, _ = _register_and_login(client, "Attachments Outsider")

        resp = client.post(
            f"/api/v1/issues/{issue_id}/attachments/prepare",
            headers=outsider_headers,
            json={
                "file_name": "private.txt",
                "mime_type": "text/plain",
                "size_bytes": 10,
            },
        )
        _assert_error(resp, 403, "FORBIDDEN")
