# Legacy схемы для демо (auth.json, project.json).
from typing import List

from pydantic import BaseModel, ConfigDict


class ProjectCategory:
    SOFTWARE = "Software"
    MARKETING = "Marketing"
    BUSINESS = "Business"


class LegacyIssueType(str):
    STORY = "Story"
    TASK = "Task"
    BUG = "Bug"


class IssueStatus(str):
    BACKLOG = "Backlog"
    SELECTED = "Selected"
    IN_PROGRESS = "InProgress"
    DONE = "Done"


class IssuePriority(str):
    LOWEST = "Lowest"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    HIGHEST = "Highest"


class UserOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    email: str
    avatarUrl: str


class CommentOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    body: str
    createdAt: str
    updatedAt: str
    issueId: str
    userId: str
    user: UserOut


class IssueOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    type: str
    status: str
    priority: str
    listPosition: int
    description: str
    createdAt: str
    updatedAt: str
    reporterId: str
    userIds: List[str]
    comments: List[CommentOut]
    projectId: str


class ProjectOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    url: str
    description: str
    category: str
    createdAt: str
    updateAt: str
    issues: List[IssueOut]
    users: List[UserOut]
