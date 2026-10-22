from pydantic import BaseModel, Field

from .meeting_schema import MeetingResponse
from .project_schema import ProjectResponse
from .task_schema import TaskResponse


class DashboardResponse(BaseModel):
    role: str
    metrics: dict[str, int]
    projects: list[ProjectResponse]
    tasks: list[TaskResponse]
    meetings: list[MeetingResponse] = Field(default_factory=list)
    upcoming_deadlines: list[TaskResponse] = Field(default_factory=list)
