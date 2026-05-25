from __future__ import annotations

import allure

from conftest import _unique_project_key


ONBOARDING_RESPONSE_REQUIRED = {"reads", "issues_to_review", "key_people", "generated_at", "cached"}
READ_ITEM_REQUIRED = {"page_id", "title", "reason"}
ISSUE_ITEM_REQUIRED = {"issue_id", "title", "reason"}
PERSON_ITEM_REQUIRED = {"user_id", "full_name", "reason"}


def _has_required(data: dict, required: set, path: str = "") -> list[str]:
    if not isinstance(data, dict):
        return [f"{path}: expected object"]
    missing = []
    for key in required:
        if key not in data:
            missing.append(f"{path}.{key}" if path else key)
    return missing


def _create_project(client, headers: dict[str, str]) -> str:
    key = _unique_project_key()
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"key": key, "name": "Onboarding Contract"},
    )
    assert project.status_code == 201, project.text
    return project.json()["project"]["id"]


@allure.epic("Contract")
@allure.feature("OpenAPI Onboarding")
class TestOnboardingContract:
    @allure.story("Recommendations")
    @allure.title("Onboarding recommendations endpoint matches contract")
    def test_onboarding_recommendations_contract(self, client, auth_headers):
        project_id = _create_project(client, auth_headers)

        first = client.get(
            f"/api/v1/projects/{project_id}/onboarding/recommendations",
            headers=auth_headers,
        )
        assert first.status_code == 200, first.text
        data = first.json()

        missing = _has_required(data, ONBOARDING_RESPONSE_REQUIRED)
        assert not missing, f"Missing response fields: {missing}"
        assert data["cached"] is False

        for item in data.get("reads", []):
            missing_item = _has_required(item, READ_ITEM_REQUIRED, "reads[]")
            assert not missing_item, f"Missing reads fields: {missing_item}"
            assert isinstance(item["reason"], str) and item["reason"]

        for item in data.get("issues_to_review", []):
            missing_item = _has_required(item, ISSUE_ITEM_REQUIRED, "issues_to_review[]")
            assert not missing_item, f"Missing issues_to_review fields: {missing_item}"
            assert isinstance(item["reason"], str) and item["reason"]

        for item in data.get("key_people", []):
            missing_item = _has_required(item, PERSON_ITEM_REQUIRED, "key_people[]")
            assert not missing_item, f"Missing key_people fields: {missing_item}"
            assert isinstance(item["reason"], str) and item["reason"]
            if item.get("email") is not None:
                assert isinstance(item["email"], str) and item["email"]

        second = client.get(
            f"/api/v1/projects/{project_id}/onboarding/recommendations",
            headers=auth_headers,
        )
        assert second.status_code == 200, second.text
        assert second.json()["cached"] is True

        forced = client.get(
            f"/api/v1/projects/{project_id}/onboarding/recommendations",
            headers=auth_headers,
            params={"force": True},
        )
        assert forced.status_code == 200, forced.text
        assert forced.json()["cached"] is False
