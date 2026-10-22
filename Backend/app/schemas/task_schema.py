from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    task_title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    project_id: int | None = None
    assigned_user_id: int | None = None
    priority: str = Field(default="Medium", max_length=50)
    status: str = Field(default="To do", max_length=50)
    due_date: date | None = None
    progress_note: str | None = None
    created_source: str = "Employee workspace"
    sequence_id: int | None = Field(default=1, ge=1)
    parent_task_id: int | None = None


class TaskUpdate(BaseModel):
    project_id: int | None = None
    assigned_user_id: int | None = None
    priority: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=50)
    due_date: date | None = None
    progress_note: str | None = None
    completion_evidence_link: str | None = None
    sequence_id: int | None = Field(default=None, ge=1)
    parent_task_id: int | None = None


class TaskOptionsResponse(BaseModel):
    projects: list[dict]
    assignees: list[dict]
    interns: list[dict]


class TaskSubmissionUpdate(BaseModel):
    completion_evidence_link: str | None = None
    progress_note: str | None = None
    progress_percentage: Decimal | None = Field(default=None, ge=0, le=100)


class TaskResponse(BaseModel):
    id: int
    task_title: str
    description: str | None = None
    project_id: int | None = None
    assigned_user_id: int | None = None
    priority: str | None = None
    status: str | None = None
    progress_percentage: Decimal = Decimal("0")
    due_date: date | None = None
    progress_note: str | None = None
    created_source: str | None = None
    completion_evidence_link: str | None = None
    submission_status: str = "Not submitted"
    project_name: str | None = None
    assigned_user_name: str | None = None
    sequence_id: int = 1
    parent_task_id: int | None = None

    model_config = ConfigDict(from_attributes=True)
