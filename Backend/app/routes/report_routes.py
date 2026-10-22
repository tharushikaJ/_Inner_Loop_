from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.project import Project
from ..models.task import Task
from ..utils.permissions import require_roles


router = APIRouter(prefix="/api/reports", tags=["reports"])
employee_or_management = require_roles("employee", "management")


@router.get("/summary")
def report_summary(_user=Depends(employee_or_management), db: Session = Depends(get_db)):
    open_task = ~func.lower(func.coalesce(Task.status, "")).in_(["completed", "done", "closed"])
    return {
        "projects": db.query(Project).count(),
        "open_tasks": db.query(Task).filter(open_task).count(),
        "overdue_tasks": db.query(Task).filter(open_task, Task.due_date < date.today()).count(),
    }
