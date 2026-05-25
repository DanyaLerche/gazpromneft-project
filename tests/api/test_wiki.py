from __future__ import annotations

import allure
import pytest

from conftest import _unique_email, _unique_project_key
from backend.services import wiki_service


@pytest.fixture
def wiki_s3_mock(monkeypatch):
    state = {"objects": set(), "deleted": []}

    class FakeS3Client:
        async def generate_presigned_post(self, Bucket, Key, Fields=None, Conditions=None, ExpiresIn=900):
            return {
                "url": "http://fake-s3.local/upload",
                "fields": {"key": Key},
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

    monkeypatch.setattr(wiki_service.aioboto3, "Session", lambda: FakeSession())
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


def _create_project(client, headers: dict[str, str], name: str = "Wiki Project") -> str:
    key = _unique_project_key()
    resp = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"key": key, "name": name},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["project"]["id"]


def _create_page(
    client,
    headers: dict[str, str],
    project_id: str,
    *,
    title: str,
    content_md: str,
    parent_id: str | None = None,
) -> dict:
    payload: dict[str, str] = {"title": title, "content_md": content_md}
    if parent_id:
        payload["parent_id"] = parent_id
    resp = client.post(
        f"/api/v1/projects/{project_id}/wiki/pages",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["page"]


@allure.epic("Wiki")
@allure.feature("Documentation pages")
class TestWikiAPI:
    @allure.story("Hierarchy")
    @allure.title("Создание и просмотр дерева страниц документации")
    def test_create_and_list_tree(self, client, auth_headers):
        project_id = _create_project(client, auth_headers)
        root = _create_page(
            client,
            auth_headers,
            project_id,
            title="Root page",
            content_md="# Root",
        )
        child = _create_page(
            client,
            auth_headers,
            project_id,
            title="Child page",
            content_md="Child text",
            parent_id=root["id"],
        )

        tree = client.get(f"/api/v1/projects/{project_id}/wiki/pages", headers=auth_headers)
        assert tree.status_code == 200, tree.text
        items = tree.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == root["id"]
        assert len(items[0]["children"]) == 1
        assert items[0]["children"][0]["id"] == child["id"]

    @allure.story("Edit and revisions")
    @allure.title("Редактирование страницы, история и rollback версии")
    def test_revisions_and_rollback(self, client, auth_headers):
        project_id = _create_project(client, auth_headers)
        page = _create_page(
            client,
            auth_headers,
            project_id,
            title="Design",
            content_md="v1",
        )
        page_id = page["id"]
        assert page["version"] == 1

        patch = client.patch(
            f"/api/v1/projects/{project_id}/wiki/pages/{page_id}",
            headers=auth_headers,
            json={"content_md": "v2", "title": "Design updated"},
        )
        assert patch.status_code == 200, patch.text
        assert patch.json()["page"]["version"] == 2

        revisions = client.get(
            f"/api/v1/projects/{project_id}/wiki/pages/{page_id}/revisions",
            headers=auth_headers,
        )
        assert revisions.status_code == 200, revisions.text
        items = revisions.json()["items"]
        versions = [item["version"] for item in items]
        assert 1 in versions and 2 in versions

        restore = client.post(
            f"/api/v1/projects/{project_id}/wiki/pages/{page_id}/restore",
            headers=auth_headers,
            json={"version": 1},
        )
        assert restore.status_code == 200, restore.text
        restored = restore.json()["page"]
        assert restored["version"] == 3
        assert restored["content_md"] == "v1"

    @allure.story("Macros")
    @allure.title("Рендер markdown с Confluence-подобными макросами")
    def test_render_macros(self, client, auth_headers):
        project_id = _create_project(client, auth_headers)
        render = client.post(
            f"/api/v1/projects/{project_id}/wiki/render",
            headers=auth_headers,
            json={
                "content_md": "{info}hello{info}\n{warning}careful{warning}\n{code:python}print('x'){code}",
            },
        )
        assert render.status_code == 200, render.text
        html = render.json()["rendered_html"]
        assert "confluence-macro info" in html
        assert "confluence-macro warning" in html
        assert "confluence-macro code" in html

    @allure.story("Attachments")
    @allure.title("Вложения wiki-страницы: prepare/create/list/download/delete")
    def test_wiki_attachments_flow(self, client, auth_headers, wiki_s3_mock):
        project_id = _create_project(client, auth_headers)
        page = _create_page(
            client,
            auth_headers,
            project_id,
            title="Attachments",
            content_md="with files",
        )
        page_id = page["id"]

        prepare = client.post(
            f"/api/v1/projects/{project_id}/wiki/pages/{page_id}/attachments/prepare",
            headers=auth_headers,
            json={"file_name": "manual.pdf", "mime_type": "application/pdf", "size_bytes": 22_000_000},
        )
        assert prepare.status_code == 200, prepare.text
        storage_key = prepare.json()["upload"]["storage_key"]
        wiki_s3_mock["objects"].add(storage_key)

        create = client.post(
            f"/api/v1/projects/{project_id}/wiki/pages/{page_id}/attachments",
            headers=auth_headers,
            json={
                "storage_key": storage_key,
                "file_name": "manual.pdf",
                "mime_type": "application/pdf",
                "size_bytes": 22_000_000,
            },
        )
        assert create.status_code == 201, create.text
        attachment_id = create.json()["attachment"]["id"]

        listed = client.get(
            f"/api/v1/projects/{project_id}/wiki/pages/{page_id}/attachments",
            headers=auth_headers,
        )
        assert listed.status_code == 200, listed.text
        assert listed.json()["items"][0]["id"] == attachment_id

        download = client.get(f"/api/v1/wiki/attachments/{attachment_id}/download", headers=auth_headers)
        assert download.status_code == 200, download.text
        assert storage_key in download.json()["download_url"]

        deleted = client.delete(f"/api/v1/wiki/attachments/{attachment_id}", headers=auth_headers)
        assert deleted.status_code == 204, deleted.text
        assert storage_key in wiki_s3_mock["deleted"]

    @allure.story("Access")
    @allure.title("Пользователь без доступа не может видеть страницы документации проекта")
    def test_wiki_forbidden_for_non_member(self, client, auth_headers):
        project_id = _create_project(client, auth_headers)
        _create_page(
            client,
            auth_headers,
            project_id,
            title="Private doc",
            content_md="secret",
        )
        outsider_headers, _ = _register_and_login(client, "Wiki Outsider")

        forbidden = client.get(f"/api/v1/projects/{project_id}/wiki/pages", headers=outsider_headers)
        assert forbidden.status_code == 403
