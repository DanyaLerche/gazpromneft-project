from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import allure

from backend.services import onboarding


@allure.epic("Onboarding")
@allure.feature("Onboarding Service")
@allure.story("Edge cases")
@allure.title("Builders return empty lists for empty project datasets")
def test_onboarding_builders_handle_empty_inputs():
    now = datetime.now(UTC)
    assert onboarding._build_reads_items([], now=now, limit=7) == []
    assert onboarding._build_issues_items([], now=now, limit=7) == []
    assert onboarding._build_people_items([], limit=5) == []


@allure.epic("Onboarding")
@allure.feature("Onboarding Service")
@allure.story("Scoring")
@allure.title("Read item contains reason and score")
def test_reads_item_has_reason_and_score():
    now = datetime.now(UTC)
    rows = [
        {
            "id": uuid4(),
            "title": "Runbook",
            "version": 4,
            "updated_at": now - timedelta(days=2),
            "revisions_count": 3,
            "attachments_count": 1,
        }
    ]
    items = onboarding._build_reads_items(rows, now=now, limit=7)
    assert len(items) == 1
    assert isinstance(items[0].reason, str) and items[0].reason
    assert items[0].score is not None


@allure.epic("Onboarding")
@allure.feature("Onboarding Service")
@allure.story("Scoring")
@allure.title("Issue and people items contain reason and score")
def test_issue_and_people_items_have_reason_and_score():
    now = datetime.now(UTC)
    issue_rows = [
        {
            "id": uuid4(),
            "key": "PRJ-10",
            "title": "Check deployment alarms",
            "parent_id": uuid4(),
            "updated_at": now - timedelta(days=1),
            "criticality_level": 3,
            "comments_count": 5,
            "worklogs_count": 2,
            "watchers_count": 4,
        }
    ]
    issue_items = onboarding._build_issues_items(issue_rows, now=now, limit=7)
    assert len(issue_items) == 1
    assert isinstance(issue_items[0].reason, str) and issue_items[0].reason
    assert issue_items[0].score is not None

    people_rows = [
        {
            "id": uuid4(),
            "full_name": "Project Admin",
            "is_project_admin": 1,
            "is_project_creator": 0,
            "activity_count": 12,
            "domain_count": 4,
        }
    ]
    people_items = onboarding._build_people_items(people_rows, limit=5)
    assert len(people_items) == 1
    assert isinstance(people_items[0].reason, str) and people_items[0].reason
    assert people_items[0].score is not None
