from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Single source of truth for signals/scoring rules.
ONBOARDING_SIGNALS_SPEC_PATH = "backend/docs/onboarding_signals.md"


class OnboardingRecommendationReason(BaseModel):
    model_config = ConfigDict(extra="ignore")

    summary: str
    facts: Dict[str, Any] = Field(default_factory=dict)


class OnboardingRecommendationItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    entity_type: Literal["wiki_page", "issue", "user"]
    title: str
    score: float = Field(ge=0, le=100)
    reason: OnboardingRecommendationReason


class OnboardingRecommendationSection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    section: Literal["wiki", "issues", "users"]
    items: List[OnboardingRecommendationItem] = Field(default_factory=list)


class OnboardingSignalsResponse(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "description": (
                "Onboarding recommendations grouped by sections. "
                f"Signals/scoring source: {ONBOARDING_SIGNALS_SPEC_PATH}"
            )
        },
    )

    project_id: UUID
    generated_at: datetime
    sections: List[OnboardingRecommendationSection] = Field(default_factory=list)


class OnboardingReadItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    page_id: UUID
    title: str
    reason: str
    score: float | None = None


class OnboardingIssueToReviewItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    issue_id: UUID
    title: str
    reason: str
    score: float | None = None


class OnboardingKeyPersonItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_id: UUID
    full_name: str
    email: str | None = None
    reason: str
    score: float | None = None


class OnboardingRecommendationsResponse(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "description": (
                "Onboarding recommendations by project. "
                f"Signals/scoring source: {ONBOARDING_SIGNALS_SPEC_PATH}"
            )
        },
    )

    reads: List[OnboardingReadItem] = Field(default_factory=list)
    issues_to_review: List[OnboardingIssueToReviewItem] = Field(default_factory=list)
    key_people: List[OnboardingKeyPersonItem] = Field(default_factory=list)
    generated_at: datetime
    cached: bool = False


class ProjectOnboardingPreferences(BaseModel):
    model_config = ConfigDict(extra="ignore")

    new_employee_mode: bool = False


class UpdateProjectOnboardingPreferencesRequest(BaseModel):
    new_employee_mode: bool


class ProjectOnboardingPreferencesResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    preferences: ProjectOnboardingPreferences


class OnboardingAssigneeItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_id: UUID
    full_name: str
    email: str | None = None


class ProjectOnboardingAssigneesResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    assignees: List[OnboardingAssigneeItem] = Field(default_factory=list)


class UpdateProjectOnboardingAssigneesRequest(BaseModel):
    user_ids: List[UUID] = Field(default_factory=list)
