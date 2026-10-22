from datetime import date, datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models.meeting import Meeting, MeetingAttendee
from ..models.user import User
from .project_service import calculated_project_progress, project_data, projects_for_user
from .task_service import task_data, tasks_for_user


DONE_STATUSES = {"completed", "done", "closed"}


def dashboard_for_user(db: Session, user: User) -> dict:
    projects = projects_for_user(db, user)
    tasks = tasks_for_user(db, user)
    open_tasks = [task for task in tasks if (task.status or "").lower() not in DONE_STATUSES]
    overdue_tasks = [task for task in open_tasks if task.due_date and task.due_date < date.today()]

    metrics = {
        "projects": len(projects),
        "total_projects": len(projects),
        "open_tasks": len(open_tasks),
        "total_tasks": len(tasks),
        "in_progress_tasks": len([task for task in tasks if (task.status or "").lower() in {"in progress", "in-progress", "active", "review", "in review"}]),
        "overdue_tasks": len(overdue_tasks),
        "completed_tasks": len(tasks) - len(open_tasks),
        "completed_projects": len([project for project in projects if (project.current_status or "").lower() in DONE_STATUSES]),
        "average_progress": round(sum(float(calculated_project_progress(db, project.id)) for project in projects) / len(projects)) if projects else 0,
        "active_projects": len([
            project for project in projects
            if (project.current_status or "").lower() in {"active", "in progress", "on track"}
        ]),
    }
    meetings = []

    if user.role in {"employee", "management"}:
        meeting_query = db.query(Meeting).filter(Meeting.start_datetime >= datetime.now())
        if user.role == "employee":
            attending_ids = db.query(MeetingAttendee.meeting_id).filter(MeetingAttendee.user_id == user.id)
            meeting_query = meeting_query.filter(or_(Meeting.created_by == user.id, Meeting.id.in_(attending_ids)))
        metrics["upcoming_meetings"] = meeting_query.count()
        meetings = meeting_query.order_by(Meeting.start_datetime.asc()).limit(5).all()

    if user.role == "management":
        metrics.update({
            "delayed_projects": len([project for project in projects if (project.current_status or "").lower() == "delayed"]),
            "blocked_projects": len([project for project in projects if (project.current_status or "").lower() == "blocked"]),
        })

    upcoming_deadlines = [
        task for task in tasks
        if task.due_date and task.due_date >= date.today() and (task.status or "").lower() not in DONE_STATUSES
    ][:6]

    return {
        "role": user.role,
        "metrics": metrics,
        "projects": [project_data(db, project) for project in projects[:5]],
        "tasks": [task_data(db, task) for task in tasks[:8]],
        "meetings": meetings,
        "upcoming_deadlines": [task_data(db, task) for task in upcoming_deadlines],
    }
