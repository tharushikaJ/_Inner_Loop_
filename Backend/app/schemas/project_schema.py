from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    project_name: str = Field(min_length=1, max_length=255)
    project_category: str | None = Field(default=None, max_length=100)
    project_description: str | None = None
    project_type: str | None = Field(default=None, max_length=100)
    responsible_employee_id: int | None = None
    current_status: str = Field(default="Planning", max_length=50)
    progress_percentage: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    current_progress_update: str | None = None
    next_activity: str | None = None
    target_date: date | None = None
    blockers: str | None = None
    related_links: str | None = None


class ProjectUpdate(BaseModel):
    project_name: str | None = Field(default=None, min_length=1, max_length=255)
    project_category: str | None = Field(default=None, max_length=100)
    project_description: str | None = None
    project_type: str | None = Field(default=None, max_length=100)
    responsible_employee_id: int | None = None
    current_status: str | None = Field(default=None, max_length=50)
    progress_percentage: Decimal | None = Field(default=None, ge=0, le=100)
    current_progress_update: str | None = None
    next_activity: str | None = None
    target_date: date | None = None
    blockers: str | None = None
    related_links: str | None = None


class ProjectOptionsResponse(BaseModel):
    employees: list[dict]


class StageTaskInfo(BaseModel):
    id: int
    task_title: str
    sequence_id: int = 1
    parent_task_id: int | None = None
    status: str | None = None
    priority: str | None = None
    assigned_user_name: str | None = None
    due_date: date | None = None


class CurrentRunningStage(BaseModel):
    sequence_id: int
    title: str
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    pending_tasks: int
    status_summary: str
    tasks: list[StageTaskInfo]


class ProjectResponse(BaseModel):
    id: int
    project_name: str
    project_category: str | None = None
    project_description: str | None = None
    project_type: str | None = None
    responsible_employee_id: int | None = None
    current_status: str | None = None
    progress_percentage: Decimal = Decimal("0")
    current_progress_update: str | None = None
    next_activity: str | None = None
    target_date: date | None = None
    blockers: str | None = None
    related_links: str | None = None
    responsible_employee_name: str | None = None
    current_running_stage: CurrentRunningStage | None = None

    model_config = ConfigDict(from_attributes=True)
