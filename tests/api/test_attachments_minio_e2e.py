from __future__ import annotations

import allure
import httpx
import pytest

from conftest import _unique_project_key
from config import settings


def _minio_available() -> bool:
    try:
        response = httpx.get("http://localhost:9000/minio/health/live", timeout=3.0)
        return response.status_code == 200
    except Exception:
        return False


def _create_project_and_issue(client, headers: dict[str, str]) -> tuple[str, str]:
    key = _unique_project_key()
    create_proj = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"key": key, "name": "Attachments E2E Project"},
    )
    assert create_proj.status_code == 201, create_proj.text
    project_id = create_proj.json()["project"]["id"]

    statuses = client.get(f"/api/v1/projects/{project_id}/statuses", headers=headers)
    assert statuses.status_code == 200, statuses.text
    status_id = statuses.json()["items"][0]["id"]

    create_issue = client.post(
        f"/api/v1/projects/{project_id}/issues",
        headers=headers,
        json={"type": "task", "title": "Attachments E2E Issue", "status_id": status_id},
    )
    assert create_issue.status_code == 201, create_issue.text
    return project_id, create_issue.json()["issue"]["id"]


@allure.epic("Attachments")
@allure.feature("E2E MinIO")
class TestAttachmentsE2E:
    @allure.story("Presigned Flow")
    @allure.title("prepare -> upload to MinIO -> confirm -> download")
    def test_presigned_upload_confirm_download_cycle(self, client, auth_headers):
        if not _minio_available():
            pytest.skip("MinIO не доступен на localhost:9000")
        if "localhost:9000" not in (settings.S3_ENDPOINT_URL or ""):
            pytest.skip("S3_ENDPOINT_URL не указывает на локальный MinIO для e2e теста")

        _, issue_id = _create_project_and_issue(client, auth_headers)
        file_bytes = b"attachment-e2e-content"
        file_name = "e2e.txt"
        mime_type = "text/plain"

        prepare = client.post(
            f"/api/v1/issues/{issue_id}/attachments/prepare",
            headers=auth_headers,
            json={
                "file_name": file_name,
                "mime_type": mime_type,
                "size_bytes": len(file_bytes),
            },
        )
        assert prepare.status_code == 200, prepare.text
        upload = prepare.json()["upload"]

        with httpx.Client(timeout=10.0) as direct_client:
            upload_resp = direct_client.post(
                upload["upload_url"],
                data=upload["fields"],
                files={"file": (file_name, file_bytes, mime_type)},
            )
        assert upload_resp.status_code in (200, 201, 204), upload_resp.text

        confirm = client.post(
            f"/api/v1/issues/{issue_id}/attachments",
            headers=auth_headers,
            json={
                "storage_key": upload["storage_key"],
                "file_name": file_name,
                "mime_type": mime_type,
                "size_bytes": len(file_bytes),
            },
        )
        assert confirm.status_code == 201, confirm.text
        attachment_id = confirm.json()["attachment"]["id"]

        get_download = client.get(f"/api/v1/attachments/{attachment_id}/download", headers=auth_headers)
        assert get_download.status_code == 200, get_download.text
        download_url = get_download.json()["download_url"]

        with httpx.Client(timeout=10.0) as direct_client:
            download_resp = direct_client.get(download_url)
        assert download_resp.status_code == 200, download_resp.text
        assert download_resp.content == file_bytes
