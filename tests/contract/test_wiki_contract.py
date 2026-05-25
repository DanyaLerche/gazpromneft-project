from __future__ import annotations

import allure
import pytest

from conftest import _unique_project_key
from backend.services import wiki_service


PAGE_REQUIRED = {
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
TREE_ITEM_REQUIRED = {"id", "project_id", "parent_id", "title", "version", "updated_at", "children"}
REVISION_REQUIRED = {
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
ATTACHMENT_REQUIRED = {
    "id",
    "page_id",
    "uploaded_by",
    "file_name",
    "mime_type",
    "size_bytes",
    "storage_key",
    "created_at",
}
UPLOAD_REQUIRED = {"storage_key", "upload_url", "headers", "fields", "method", "expires_in"}


def _has_required(data: dict, required: set, path: str = "") -> list[str]:
    if not isinstance(data, dict):
        return [f"{path}: expected object"]
    missing = []
    for key in required:
        if key not in data:
            missing.append(f"{path}.{key}" if path else key)
    return missing


@pytest.fixture
def wiki_s3_mock(monkeypatch):
    state = {"objects": set(), "deleted": []}

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

    monkeypatch.setattr(wiki_service.aioboto3, "Session", lambda: FakeSession())
    return state


def _create_project(client, headers: dict[str, str]) -> str:
    key = _unique_project_key()
    project = client.post("/api/v1/projects", headers=headers, json={"key": key, "name": "Wiki Contract"})
    assert project.status_code == 201, project.text
    return project.json()["project"]["id"]


@allure.epic("Contract")
@allure.feature("OpenAPI Wiki")
class TestWikiContract:
    @allure.story("Pages")
    @allure.title("Wiki pages endpoints соответствуют контракту")
    def test_pages_contract(self, client, auth_headers):
        project_id = _create_project(client, auth_headers)

        created = client.post(
            f"/api/v1/projects/{project_id}/wiki/pages",
            headers=auth_headers,
            json={"title": "Contract page", "content_md": "# Contract"},
        )
        assert created.status_code == 201, created.text
        assert "page" in created.json()
        missing = _has_required(created.json()["page"], PAGE_REQUIRED, "page")
        assert not missing, f"Missing: {missing}"
        page_id = created.json()["page"]["id"]

        listed = client.get(f"/api/v1/projects/{project_id}/wiki/pages", headers=auth_headers)
        assert listed.status_code == 200, listed.text
        assert "items" in listed.json()
        if listed.json()["items"]:
            missing_tree = _has_required(listed.json()["items"][0], TREE_ITEM_REQUIRED, "items[]")
            assert not missing_tree, f"Missing tree fields: {missing_tree}"

        page = client.get(f"/api/v1/projects/{project_id}/wiki/pages/{page_id}", headers=auth_headers)
        assert page.status_code == 200, page.text
        missing_get = _has_required(page.json()["page"], PAGE_REQUIRED, "page")
        assert not missing_get, f"Missing page fields: {missing_get}"

    @allure.story("Render and revisions")
    @allure.title("Render и revision endpoints соответствуют контракту")
    def test_render_and_revisions_contract(self, client, auth_headers):
        project_id = _create_project(client, auth_headers)
        created = client.post(
            f"/api/v1/projects/{project_id}/wiki/pages",
            headers=auth_headers,
            json={"title": "History page", "content_md": "v1"},
        )
        page_id = created.json()["page"]["id"]

        rendered = client.post(
            f"/api/v1/projects/{project_id}/wiki/render",
            headers=auth_headers,
            json={"content_md": "{info}hello{info}"},
        )
        assert rendered.status_code == 200, rendered.text
        assert "rendered_html" in rendered.json()

        updated = client.patch(
            f"/api/v1/projects/{project_id}/wiki/pages/{page_id}",
            headers=auth_headers,
            json={"content_md": "v2"},
        )
        assert updated.status_code == 200, updated.text
        missing_updated = _has_required(updated.json()["page"], PAGE_REQUIRED, "page")
        assert not missing_updated, f"Missing page fields: {missing_updated}"

        revisions = client.get(
            f"/api/v1/projects/{project_id}/wiki/pages/{page_id}/revisions",
            headers=auth_headers,
        )
        assert revisions.status_code == 200, revisions.text
        assert "items" in revisions.json()
        if revisions.json()["items"]:
            missing_rev = _has_required(revisions.json()["items"][0], REVISION_REQUIRED, "items[]")
            assert not missing_rev, f"Missing revision fields: {missing_rev}"

        restored = client.post(
            f"/api/v1/projects/{project_id}/wiki/pages/{page_id}/restore",
            headers=auth_headers,
            json={"version": 1},
        )
        assert restored.status_code == 200, restored.text
        missing_restored = _has_required(restored.json()["page"], PAGE_REQUIRED, "page")
        assert not missing_restored, f"Missing page fields: {missing_restored}"

    @allure.story("Attachments")
    @allure.title("Wiki attachments endpoints соответствуют контракту")
    def test_attachments_contract(self, client, auth_headers, wiki_s3_mock):
        project_id = _create_project(client, auth_headers)
        page = client.post(
            f"/api/v1/projects/{project_id}/wiki/pages",
            headers=auth_headers,
            json={"title": "Attachments page", "content_md": "files"},
        )
        page_id = page.json()["page"]["id"]

        prepare = client.post(
            f"/api/v1/projects/{project_id}/wiki/pages/{page_id}/attachments/prepare",
            headers=auth_headers,
            json={"file_name": "contract.bin", "mime_type": "application/octet-stream", "size_bytes": 25_000_000},
        )
        assert prepare.status_code == 200, prepare.text
        assert "upload" in prepare.json()
        missing_upload = _has_required(prepare.json()["upload"], UPLOAD_REQUIRED, "upload")
        assert not missing_upload, f"Missing upload fields: {missing_upload}"
        storage_key = prepare.json()["upload"]["storage_key"]
        wiki_s3_mock["objects"].add(storage_key)

        created = client.post(
            f"/api/v1/projects/{project_id}/wiki/pages/{page_id}/attachments",
            headers=auth_headers,
            json={
                "storage_key": storage_key,
                "file_name": "contract.bin",
                "mime_type": "application/octet-stream",
                "size_bytes": 25_000_000,
            },
        )
        assert created.status_code == 201, created.text
        missing_attachment = _has_required(created.json()["attachment"], ATTACHMENT_REQUIRED, "attachment")
        assert not missing_attachment, f"Missing attachment fields: {missing_attachment}"
        attachment_id = created.json()["attachment"]["id"]

        listed = client.get(
            f"/api/v1/projects/{project_id}/wiki/pages/{page_id}/attachments",
            headers=auth_headers,
        )
        assert listed.status_code == 200, listed.text
        assert "items" in listed.json()
        if listed.json()["items"]:
            missing_list_item = _has_required(listed.json()["items"][0], ATTACHMENT_REQUIRED, "items[]")
            assert not missing_list_item, f"Missing list fields: {missing_list_item}"

        download = client.get(f"/api/v1/wiki/attachments/{attachment_id}/download", headers=auth_headers)
        assert download.status_code == 200, download.text
        assert "download_url" in download.json()
