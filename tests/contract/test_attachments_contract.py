from __future__ import annotations

import allure
import pytest

from conftest import _unique_project_key
from backend.services import attachments_service


ATTACHMENT_REQUIRED = {
    "id",
    "issue_id",
    "uploaded_by",
    "file_name",
    "mime_type",
    "size_bytes",
    "storage_key",
    "created_at",
}
PREPARE_RESPONSE_REQUIRED = {"upload"}
UPLOAD_REQUIRED = {"storage_key", "upload_url", "headers", "fields", "method", "expires_in"}
LIST_REQUIRED = {"items"}
DOWNLOAD_REQUIRED = {"download_url"}
ERROR_REQUIRED = {"code", "message"}


def _has_required(data: dict, required: set, path: str = "") -> list[str]:
    if not isinstance(data, dict):
        return [f"{path}: expected object"]
    missing = []
    for key in required:
        if key not in data:
            missing.append(f"{path}.{key}" if path else key)
    return missing


@pytest.fixture
def s3_mock(monkeypatch):
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

    monkeypatch.setattr(attachments_service.aioboto3, "Session", lambda: FakeSession())
    return state


def _create_issue(client, headers: dict[str, str]) -> str:
    key = _unique_project_key()
    project = client.post("/api/v1/projects", headers=headers, json={"key": key, "name": "Attachment Contract"})
    assert project.status_code == 201, project.text
    project_id = project.json()["project"]["id"]

    statuses = client.get(f"/api/v1/projects/{project_id}/statuses", headers=headers)
    assert statuses.status_code == 200, statuses.text
    status_id = statuses.json()["items"][0]["id"]

    issue = client.post(
        f"/api/v1/projects/{project_id}/issues",
        headers=headers,
        json={"type": "task", "title": "Attachment contract issue", "status_id": status_id},
    )
    assert issue.status_code == 201, issue.text
    return issue.json()["issue"]["id"]


@allure.epic("Contract")
@allure.feature("OpenAPI Attachments")
class TestAttachmentsContract:
    @allure.story("Prepare")
    @allure.title("PrepareAttachmentResponse соответствует контракту")
    def test_prepare_attachment_contract(self, client, auth_headers, s3_mock):
        issue_id = _create_issue(client, auth_headers)
        resp = client.post(
            f"/api/v1/issues/{issue_id}/attachments/prepare",
            headers=auth_headers,
            json={"file_name": "contract.txt", "mime_type": "text/plain", "size_bytes": 10},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        missing = _has_required(data, PREPARE_RESPONSE_REQUIRED)
        assert not missing, f"Missing: {missing}"
        missing_upload = _has_required(data["upload"], UPLOAD_REQUIRED, "upload")
        assert not missing_upload, f"upload missing: {missing_upload}"

    @allure.story("Create/List/Download")
    @allure.title("IssueAttachment, list и download соответствуют контракту")
    def test_create_list_download_attachment_contract(self, client, auth_headers, s3_mock):
        issue_id = _create_issue(client, auth_headers)
        prepare = client.post(
            f"/api/v1/issues/{issue_id}/attachments/prepare",
            headers=auth_headers,
            json={"file_name": "diagram.svg", "mime_type": "image/svg+xml", "size_bytes": 100},
        )
        storage_key = prepare.json()["upload"]["storage_key"]
        s3_mock["objects"].add(storage_key)

        created = client.post(
            f"/api/v1/issues/{issue_id}/attachments",
            headers=auth_headers,
            json={
                "storage_key": storage_key,
                "file_name": "diagram.svg",
                "mime_type": "image/svg+xml",
                "size_bytes": 100,
            },
        )
        assert created.status_code == 201, created.text
        attachment = created.json()["attachment"]
        missing_attachment = _has_required(attachment, ATTACHMENT_REQUIRED, "attachment")
        assert not missing_attachment, f"attachment missing: {missing_attachment}"

        listed = client.get(f"/api/v1/issues/{issue_id}/attachments", headers=auth_headers)
        assert listed.status_code == 200, listed.text
        missing_list = _has_required(listed.json(), LIST_REQUIRED)
        assert not missing_list, f"list missing: {missing_list}"
        item_missing = _has_required(listed.json()["items"][0], ATTACHMENT_REQUIRED, "items[]")
        assert not item_missing, f"list item missing: {item_missing}"

        attachment_id = attachment["id"]
        download = client.get(f"/api/v1/attachments/{attachment_id}/download", headers=auth_headers)
        assert download.status_code == 200, download.text
        missing_download = _has_required(download.json(), DOWNLOAD_REQUIRED)
        assert not missing_download, f"download missing: {missing_download}"

    @allure.story("Errors")
    @allure.title("Ошибки attachments возвращаются в формате ErrorResponse")
    def test_attachment_error_response_contract(self, client):
        resp = client.get("/api/v1/attachments/00000000-0000-0000-0000-000000000000/download")
        assert resp.status_code == 401, resp.text
        payload = resp.json()
        assert "error" in payload
        missing_error = _has_required(payload["error"], ERROR_REQUIRED, "error")
        assert not missing_error, f"error missing: {missing_error}"
