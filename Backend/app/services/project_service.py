from fastapi import HTTPException, status
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models.project import Project
from ..models.task import Task
from ..models.user import User
from ..schemas.project_schema import ProjectCreate, ProjectUpdate


def intern_project_ids(db: Session, user_id: int) -> list[int]:
    return [
        row[0]
        for row in db.query(Task.project_id)
        .filter(Task.assigned_user_id == user_id, Task.project_id.is_not(None))
        .distinct()
        .all()
    ]


def projects_for_user(db: Session, user: User) -> list[Project]:
    query = db.query(Project)
    if user.role == "employee":
        query = query.filter(Project.responsible_employee_id == user.id)
    elif user.role == "intern":
        project_ids = intern_project_ids(db, user.id)
        if not project_ids:
            return []
        query = query.filter(Project.id.in_(project_ids))
    return query.order_by(Project.updated_at.desc(), Project.id.desc()).all()


DONE_STATUSES = {"completed", "complete", "done", "closed", "approved"}


def calculated_project_progress(db: Session, project_id: int) -> Decimal:
    statuses = db.query(Task.status).filter(Task.project_id == project_id).all()
    if not statuses:
        project = db.query(Project.progress_percentage).filter(Project.id == project_id).first()
        return project[0] if project and project[0] is not None else Decimal("0")
    completed = sum((task_status or "").lower() in DONE_STATUSES for (task_status,) in statuses)
    return (Decimal(completed * 100) / Decimal(len(statuses))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_current_running_stage(db: Session, project_id: int) -> dict | None:
    tasks = db.query(Task).filter(Task.project_id == project_id).order_by(Task.sequence_id.asc(), Task.id.asc()).all()
    if not tasks:
        return None

    grouped: dict[int, list[Task]] = {}
    for task in tasks:
        seq = task.sequence_id if task.sequence_id is not None else 1
        grouped.setdefault(seq, []).append(task)

    running_seq = None
    for seq in sorted(grouped.keys()):
        seq_tasks = grouped[seq]
        if any((t.status or "").lower() not in DONE_STATUSES for t in seq_tasks):
            running_seq = seq
            break

    if running_seq is None:
        running_seq = max(grouped.keys())

    current_tasks = grouped[running_seq]
    total = len(current_tasks)
    completed = sum((t.status or "").lower() in DONE_STATUSES for t in current_tasks)
    in_prog = sum((t.status or "").lower() in {"in progress", "in-progress", "active"} for t in current_tasks)
    pending = total - completed - in_prog

    user_ids = {t.assigned_user_id for t in current_tasks if t.assigned_user_id}
    users_map = {u.id: u.name for u in db.query(User.id, User.name).filter(User.id.in_(user_ids)).all()} if user_ids else {}

    stage_tasks = [
        {
            "id": t.id,
            "task_title": t.task_title,
            "sequence_id": t.sequence_id or 1,
            "parent_task_id": t.parent_task_id,
            "status": t.status or "To do",
            "priority": t.priority or "Normal",
            "assigned_user_name": users_map.get(t.assigned_user_id),
            "due_date": t.due_date,
        }
        for t in current_tasks
    ]

    title = current_tasks[0].task_title if total == 1 else f"Stage {running_seq} ({total} tasks)"
    status_summary = f"{completed}/{total} completed" + (f" · {in_prog} in progress" if in_prog else "")

    return {
        "sequence_id": running_seq,
        "title": title,
        "total_tasks": total,
        "completed_tasks": completed,
        "in_progress_tasks": in_prog,
        "pending_tasks": pending,
        "status_summary": status_summary,
        "tasks": stage_tasks,
    }


def project_data(db: Session, project: Project) -> dict:
    employee_name = None
    if project.responsible_employee_id:
        employee_name = db.query(User.name).filter(User.id == project.responsible_employee_id).scalar()
    progress = calculated_project_progress(db, project.id)
    running_stage = get_current_running_stage(db, project.id)
    return {
        column.name: getattr(project, column.name)
        for column in Project.__table__.columns
    } | {
        "progress_percentage": progress,
        "responsible_employee_name": employee_name,
        "current_running_stage": running_stage,
    }


def project_records_for_user(db: Session, user: User) -> list[dict]:
    return [project_data(db, project) for project in projects_for_user(db, user)]


def project_options(db: Session) -> dict:
    return {
        "employees": [
            {"id": employee.id, "name": employee.name, "designation": employee.designation}
            for employee in db.query(User)
            .filter(User.role == "employee", User.status == "active")
            .order_by(User.name.asc())
            .all()
        ],
    }


def create_project(
    db: Session,
    payload: ProjectCreate,
    default_responsible_employee_id: int | None = None,
) -> dict:
    values = payload.model_dump()
    if values["responsible_employee_id"] is None:
        values["responsible_employee_id"] = default_responsible_employee_id
    if values["responsible_employee_id"] is not None:
        employee_exists = db.query(User.id).filter(
            User.id == values["responsible_employee_id"],
            User.role == "employee",
            User.status == "active",
        ).first()
        if not employee_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The selected responsible employee is not active or does not exist.",
            )
    project = Project(**values)
    db.add(project)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected responsible employee does not exist.",
        ) from error
    db.refresh(project)
    return project_data(db, project)


def _validate_project_relationships(db: Session, values: dict) -> None:
    if "responsible_employee_id" in values and values["responsible_employee_id"] is not None:
        employee_exists = db.query(User.id).filter(
            User.id == values["responsible_employee_id"],
            User.role == "employee",
            User.status == "active",
        ).first()
        if not employee_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The selected responsible employee is not active or does not exist.",
            )


def _employee_project(db: Session, project_id: int, employee_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    if project.responsible_employee_id != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify projects assigned to you.",
        )
    return project


def update_project(
    db: Session,
    project_id: int,
    employee_id: int,
    payload: ProjectUpdate,
) -> dict:
    project = _employee_project(db, project_id, employee_id)
    values = payload.model_dump(exclude_unset=True)
    if not values:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one project field to update.",
        )
    if "project_name" in values and values["project_name"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project name cannot be null.",
        )
    _validate_project_relationships(db, values)
    for field, value in values.items():
        setattr(project, field, value)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected responsible employee does not exist.",
        ) from error
    db.refresh(project)
    return project_data(db, project)


def _project_dependency_counts(db: Session, project_id: int) -> dict[str, int]:
    dependency_columns = {
        "tasks": "project_id",
        "project_updates": "project_id",
        "meeting_projects": "project_id",
        "documents": "project_id",
    }
    inspector = inspect(db.get_bind())
    existing_tables = set(inspector.get_table_names())
    counts = {}
    for table_name, column_name in dependency_columns.items():
        if table_name in existing_tables:
            counts[table_name] = db.execute(
                text(f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} = :project_id"),
                {"project_id": project_id},
            ).scalar_one()
    return {name: count for name, count in counts.items() if count}


def delete_project(db: Session, project_id: int, employee_id: int) -> None:
    project = _employee_project(db, project_id, employee_id)
    dependencies = _project_dependency_counts(db, project_id)
    if dependencies:
        labels = {
            "tasks": "task(s)",
            "project_updates": "project update(s)",
            "meeting_projects": "meeting link(s)",
            "documents": "document(s)",
        }
        summary = ", ".join(f"{count} {labels[name]}" for name, count in dependencies.items())
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This project cannot be deleted while it has related records: {summary}. Remove or reassign them first.",
        )
    db.delete(project)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This project cannot be deleted while related records still exist.",
        ) from error
