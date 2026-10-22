from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.meeting import Meeting, MeetingAttendee
from app.models.project import Project
from app.models.room import MeetingRoom
from app.models.task import Task
from app.models.user import User


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    client.cookies.clear()
    yield


def register(payload):
    return client.post("/api/auth/register", json=payload)


def login(email):
    client.cookies.clear()
    return client.post("/api/auth/login", json={
        "email": email,
        "password": "Password123",
    })


def test_registers_all_supported_roles_without_exposing_password_hash():
    intern = register({
        "name": "Ishan Intern",
        "email": "intern@example.com",
        "password": "Password123",
        "role": "intern",
    })
    assert intern.status_code == 201
    assert intern.json()["user"]["role"] == "intern"
    assert intern.json()["user"]["designation"] is None
    assert "password_hash" not in intern.json()["user"]

    employee = register({
        "name": "Esha Employee",
        "email": "employee@example.com",
        "password": "Password123",
        "role": "employee",
        "designation": "Software Engineer",
        "department": "Digital Lab",
    })
    assert employee.status_code == 201
    assert employee.json()["user"]["designation"] == "Software Engineer"
    assert employee.json()["user"]["assigned_supervisor_id"] is None

    management = register({
        "name": "Manoj Manager",
        "email": "management@example.com",
        "password": "Password123",
        "role": "management",
        "designation": "Project Manager",
        "department": "Digital Lab",
    })
    assert management.status_code == 201
    assert management.json()["user"]["role"] == "management"
    assert management.json()["user"]["assigned_supervisor_id"] is None


def test_registration_validation_and_duplicate_email():
    payload = {
        "name": "Esha Employee",
        "email": "employee@example.com",
        "password": "Password123",
        "role": "employee",
    }
    assert register(payload).status_code == 422

    payload.update({"designation": "Engineer", "department": "Digital Lab"})
    assert register(payload).status_code == 201
    assert register(payload).status_code == 409

    assert register({
        "name": "Invalid Role",
        "email": "invalid@example.com",
        "password": "Password123",
        "role": "administrator",
    }).status_code == 422


def test_login_me_logout_and_generic_login_failures():
    register({
        "name": "Ishan Intern",
        "email": "intern@example.com",
        "password": "Password123",
        "role": "intern",
    })

    for credentials in (
        {"email": "intern@example.com", "password": "wrong-password"},
        {"email": "missing@example.com", "password": "Password123"},
    ):
        response = client.post("/api/auth/login", json=credentials)
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password."

    login = client.post("/api/auth/login", json={
        "email": "intern@example.com",
        "password": "Password123",
    })
    assert login.status_code == 200
    assert "innerloop_access_token" in login.cookies
    assert "password_hash" not in login.json()["user"]
    assert login.json()["user"]["role"] == "intern"

    assert client.post("/api/auth/login", json={
        "email": "intern@example.com",
        "password": "Password123",
        "role": "intern",
    }).status_code == 422

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "intern@example.com"

    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_inactive_user_cannot_login():
    register({
        "name": "Inactive User",
        "email": "inactive@example.com",
        "password": "Password123",
        "role": "intern",
    })
    with TestingSession() as db:
        user = db.query(User).filter(User.email == "inactive@example.com").one()
        user.status = "inactive"
        db.commit()

    response = client.post("/api/auth/login", json={
        "email": "inactive@example.com",
        "password": "Password123",
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def seed_rbac_workspace():
    users = [
        {"name": "Ishan Intern", "email": "intern@example.com", "password": "Password123", "role": "intern"},
        {"name": "Nadia Intern", "email": "intern2@example.com", "password": "Password123", "role": "intern"},
        {"name": "Esha Employee", "email": "employee@example.com", "password": "Password123", "role": "employee", "designation": "Engineer", "department": "Digital Lab"},
        {"name": "Manoj Manager", "email": "management@example.com", "password": "Password123", "role": "management", "designation": "Manager", "department": "Digital Lab"},
    ]
    for payload in users:
        assert register(payload).status_code == 201

    with TestingSession() as db:
        intern = db.query(User).filter(User.email == "intern@example.com").one()
        other_intern = db.query(User).filter(User.email == "intern2@example.com").one()
        employee = db.query(User).filter(User.email == "employee@example.com").one()
        direct_project = Project(project_name="Assigned Project", responsible_employee_id=employee.id, current_status="active", progress_percentage=60)
        other_project = Project(project_name="Other Project", current_status="blocked", progress_percentage=20)
        reverse_project = Project(project_name="Reverse Assigned Project", current_status="active", progress_percentage=40)
        db.add_all([direct_project, other_project, reverse_project])
        db.flush()

        db.add_all([
            Task(task_title="Direct Task", project_id=direct_project.id, assigned_user_id=intern.id, status="in progress"),
            Task(task_title="Reverse Project Task", project_id=reverse_project.id, assigned_user_id=intern.id, status="todo"),
            Task(task_title="Other Intern Task", project_id=other_project.id, assigned_user_id=other_intern.id, status="todo"),
            Task(task_title="Employee Task", assigned_user_id=employee.id, status="todo"),
            Task(task_title="Responsible Project Task", project_id=direct_project.id, status="in progress"),
            Task(task_title="Unassigned Task", status="todo"),
        ])
        db.commit()


def test_intern_data_is_sql_scoped_and_privileged_routes_are_forbidden():
    seed_rbac_workspace()
    assert login("intern@example.com").status_code == 200

    projects = client.get("/api/projects")
    assert projects.status_code == 200
    assert {item["project_name"] for item in projects.json()} == {"Assigned Project", "Reverse Assigned Project"}

    tasks = client.get("/api/tasks")
    assert tasks.status_code == 200
    assert {item["task_title"] for item in tasks.json()} == {"Direct Task", "Reverse Project Task", "Responsible Project Task"}

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["role"] == "intern"
    assert dashboard.json()["metrics"]["projects"] == 2
    assert dashboard.json()["metrics"]["open_tasks"] == 3

    assert client.get("/api/meetings").status_code == 200
    assert client.get("/api/meetings/options").status_code == 403

    for path in ("/api/meeting-rooms", "/api/reports/summary", "/api/users", "/api/settings", "/api/audit-logs"):
        assert client.get(path).status_code == 403


def test_intern_calendar_only_returns_meetings_where_they_are_an_attendee():
    seed_rbac_workspace()
    with TestingSession() as db:
        intern = db.query(User).filter(User.email == "intern@example.com").one()
        other_intern = db.query(User).filter(User.email == "intern2@example.com").one()
        employee = db.query(User).filter(User.email == "employee@example.com").one()
        intern_id = intern.id
        invited_meeting = Meeting(
            meeting_title="Intern planning session",
            start_datetime=datetime(2032, 1, 10, 9, 0),
            end_datetime=datetime(2032, 1, 10, 10, 0),
            created_by=employee.id,
        )
        other_meeting = Meeting(
            meeting_title="Other intern session",
            start_datetime=datetime(2032, 1, 11, 9, 0),
            end_datetime=datetime(2032, 1, 11, 10, 0),
            created_by=employee.id,
        )
        db.add_all([invited_meeting, other_meeting])
        db.flush()
        db.add_all([
            MeetingAttendee(meeting_id=invited_meeting.id, user_id=intern.id, attendance_status="Invited"),
            MeetingAttendee(meeting_id=other_meeting.id, user_id=other_intern.id, attendance_status="Invited"),
        ])
        db.commit()

    assert login("intern@example.com").status_code == 200
    meetings = client.get("/api/meetings")

    assert meetings.status_code == 200
    assert [meeting["meeting_title"] for meeting in meetings.json()] == ["Intern planning session"]
    assert meetings.json()[0]["current_user_attendance_status"] == "Invited"
    assert meetings.json()[0]["accepted_attendee_count"] == 0
    notifications = client.get("/api/notifications")
    assert notifications.status_code == 200
    assert [notification["meeting_id"] for notification in notifications.json()] == [meetings.json()[0]["id"]]
    assert notifications.json()[0]["title"] == "New meeting invitation"
    assert client.delete(f"/api/notifications/{notifications.json()[0]['id']}").status_code == 204
    assert client.get("/api/notifications").json() == []

    accepted = client.patch(
        f"/api/meetings/{meetings.json()[0]['id']}/attendance",
        json={"attendance_status": "Accepted"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["current_user_attendance_status"] == "Accepted"
    assert accepted.json()["accepted_attendee_count"] == 1
    assert client.get("/api/notifications").json() == []

    assert login("employee@example.com").status_code == 200
    employee_notifications = client.get("/api/notifications")
    assert employee_notifications.status_code == 200
    assert len(employee_notifications.json()) == 1
    assert employee_notifications.json()[0]["notification_type"] == "meeting_invitation_accepted"
    assert employee_notifications.json()[0]["meeting_id"] == accepted.json()["id"]
    assert "Ishan Intern accepted" in employee_notifications.json()[0]["message"]
    assert client.delete(f"/api/notifications/{employee_notifications.json()[0]['id']}").status_code == 204
    assert client.get("/api/notifications").json() == []
    edited = client.put(
        f"/api/meetings/{accepted.json()['id']}",
        json={
            "meeting_title": "Updated intern planning session",
            "start_datetime": "2032-01-10T09:00:00",
            "end_datetime": "2032-01-10T10:00:00",
            "attendee_user_ids": [intern_id],
        },
    )
    assert edited.status_code == 200
    assert edited.json()["accepted_attendee_count"] == 1

    assert login("management@example.com").status_code == 200
    management_meetings = client.get("/api/meetings").json()
    assert {meeting["meeting_title"] for meeting in management_meetings} == {
        "Updated intern planning session",
        "Other intern session",
    }
    accepted_for_management = next(meeting for meeting in management_meetings if meeting["meeting_title"] == "Updated intern planning session")
    assert accepted_for_management["accepted_attendee_count"] == 1
    assert accepted_for_management["current_user_attendance_status"] is None
    assert client.patch(
        f"/api/meetings/{accepted_for_management['id']}/attendance",
        json={"attendance_status": "Declined"},
    ).status_code == 403

    assert login("intern@example.com").status_code == 200
    declined = client.patch(
        f"/api/meetings/{accepted_for_management['id']}/attendance",
        json={"attendance_status": "Declined"},
    )
    assert declined.status_code == 200
    assert declined.json()["current_user_attendance_status"] == "Declined"
    assert declined.json()["accepted_attendee_count"] == 0


def test_intern_can_only_update_directly_assigned_tasks_in_visible_projects():
    seed_rbac_workspace()
    with TestingSession() as db:
        intern = db.query(User).filter(User.email == "intern@example.com").one()
        reverse_project = db.query(Project).filter(Project.project_name == "Reverse Assigned Project").one()
        other_project = db.query(Project).filter(Project.project_name == "Other Project").one()
        reverse_task = Task(task_title="Read-only Project Task", project_id=reverse_project.id, status="To do")
        assigned_reverse_task = Task(
            task_title="Assigned Reverse Project Task",
            project_id=reverse_project.id,
            assigned_user_id=intern.id,
            status="To do",
        )
        other_task = Task(task_title="Other Project Task", project_id=other_project.id, status="todo")
        db.add_all([reverse_task, assigned_reverse_task, other_task])
        db.commit()
        reverse_task_id = reverse_task.id
        assigned_reverse_task_id = assigned_reverse_task.id
        other_task_id = other_task.id

    assert login("intern@example.com").status_code == 200
    visible_projects = {item["project_name"] for item in client.get("/api/projects").json()}
    visible_tasks = {item["task_title"] for item in client.get("/api/tasks").json()}

    assert visible_projects == {"Assigned Project", "Reverse Assigned Project"}
    assert "Read-only Project Task" in visible_tasks
    assert "Assigned Reverse Project Task" in visible_tasks
    assert "Other Project Task" not in visible_tasks

    assert client.patch(f"/api/tasks/{reverse_task_id}", json={"status": "In progress"}).status_code == 403
    assert client.patch(
        f"/api/tasks/{reverse_task_id}/submission",
        json={"progress_note": "Should remain read-only."},
    ).status_code == 403

    for next_status in ("In progress", "Completed", "To do"):
        updated = client.patch(f"/api/tasks/{assigned_reverse_task_id}", json={"status": next_status})
        assert updated.status_code == 200
        assert updated.json()["status"] == next_status
    assert client.patch(f"/api/tasks/{assigned_reverse_task_id}", json={"status": "Review"}).status_code == 422

    assert client.patch(
        f"/api/tasks/{other_task_id}/submission",
        json={"progress_note": "Should not be accepted.", "progress_percentage": 50},
    ).status_code == 403


def test_employee_can_use_operational_routes_but_not_administration():
    seed_rbac_workspace()
    assert login("employee@example.com").status_code == 200

    for path in ("/api/dashboard", "/api/projects", "/api/tasks", "/api/meetings", "/api/meeting-rooms", "/api/reports/summary"):
        assert client.get(path).status_code == 200
    assert {item["project_name"] for item in client.get("/api/projects").json()} == {"Assigned Project"}
    assert {item["task_title"] for item in client.get("/api/tasks").json()} == {"Direct Task", "Employee Task", "Responsible Project Task"}
    for path in ("/api/users", "/api/settings", "/api/audit-logs"):
        assert client.get(path).status_code == 403


def test_management_can_use_every_rbac_route():
    seed_rbac_workspace()
    assert login("management@example.com").status_code == 200

    for path in ("/api/dashboard", "/api/projects", "/api/tasks", "/api/meetings", "/api/meeting-rooms", "/api/reports/summary", "/api/users", "/api/settings", "/api/audit-logs"):
        assert client.get(path).status_code == 200
    metrics = client.get("/api/dashboard").json()["metrics"]
    assert metrics["active_projects"] == 2
    assert metrics["blocked_projects"] == 1
    assert metrics["delayed_projects"] == 0


def test_meetings_support_scheduling_room_conflicts_and_owner_permissions():
    seed_rbac_workspace()
    with TestingSession() as db:
        room = MeetingRoom(room_name="Blue Room", status="Available")
        db.add(room)
        db.commit()
        db.refresh(room)
        room_id = room.id

    assert login("employee@example.com").status_code == 200
    meeting = client.post("/api/meetings", json={
        "meeting_title": "Weekly delivery sync",
        "meeting_type": "Team sync",
        "start_datetime": "2026-10-08T10:00:00",
        "end_datetime": "2026-10-08T11:00:00",
        "meeting_room_id": room_id,
        "attendee_user_ids": [],
        "project_ids": [],
    })
    assert meeting.status_code == 201
    meeting_id = meeting.json()["id"]
    assert len(client.get("/api/meetings").json()) == 1

    conflict = client.post("/api/meetings", json={
        "meeting_title": "Conflicting sync",
        "start_datetime": "2026-10-08T10:30:00",
        "end_datetime": "2026-10-08T11:30:00",
        "meeting_room_id": room_id,
    })
    assert conflict.status_code == 409

    assert client.put(f"/api/meetings/{meeting_id}", json={
        "meeting_title": "Updated delivery sync",
        "start_datetime": "2026-10-08T10:00:00",
        "end_datetime": "2026-10-08T11:00:00",
        "meeting_room_id": room_id,
    }).status_code == 200

    assert login("management@example.com").status_code == 200
    assert client.delete(f"/api/meetings/{meeting_id}").status_code == 204


def test_employee_meeting_options_only_include_assigned_interns():
    seed_rbac_workspace()
    with TestingSession() as db:
        employee = db.query(User).filter(User.email == "employee@example.com").one()
        assigned_intern = db.query(User).filter(User.email == "intern@example.com").one()
        assigned_intern.assigned_supervisor_id = employee.id
        db.commit()

    assert login("employee@example.com").status_code == 200
    options = client.get("/api/meetings/options")

    assert options.status_code == 200
    assert {attendee["name"] for attendee in options.json()["attendees"]} == {"Ishan Intern"}

    assert login("management@example.com").status_code == 200
    management_options = client.get("/api/meetings/options")

    assert management_options.status_code == 200
    assert {"Ishan Intern", "Nadia Intern"}.issubset(
        {attendee["name"] for attendee in management_options.json()["attendees"]}
    )


def test_employee_can_create_projects_and_tasks_that_persist_with_existing_visibility_rules():
    seed_rbac_workspace()
    with TestingSession() as db:
        employee = db.query(User).filter(User.email == "employee@example.com").one()
        assigned_intern = db.query(User).filter(User.email == "intern@example.com").one()
        assigned_intern.assigned_supervisor_id = employee.id
        db.commit()
    assert login("employee@example.com").status_code == 200

    project_options = client.get("/api/projects/options")
    assert project_options.status_code == 200
    employee_id = next(item["id"] for item in project_options.json()["employees"] if item["name"] == "Esha Employee")

    task_options = client.get("/api/tasks/options")
    assert task_options.status_code == 200
    assert all(item["email"] for item in task_options.json()["assignees"])
    assert {item["name"] for item in task_options.json()["interns"]} == {"Ishan Intern"}
    assert all(item["email"] and set(item) == {"id", "name", "email"} for item in task_options.json()["interns"])
    assert "Nadia Intern" not in {item["name"] for item in task_options.json()["assignees"]}

    project = client.post("/api/projects", json={
        "project_name": "Persistent Delivery Project",
        "project_category": "Platform",
        "current_status": "Active",
        "progress_percentage": 25,
        "target_date": "2030-01-15",
    })
    assert project.status_code == 201
    project_id = project.json()["id"]
    assert project.json()["responsible_employee_id"] == employee_id
    assert project.json()["responsible_employee_name"] == "Esha Employee"

    task = client.post("/api/tasks", json={
        "task_title": "Persistent Delivery Task",
        "project_id": project_id,
        "priority": "High",
        "status": "To do",
        "due_date": "2030-01-10",
    })
    assert task.status_code == 201
    assert task.json()["assigned_user_id"] == employee_id
    assert task.json()["project_name"] == "Persistent Delivery Project"
    assert task.json()["assigned_user_name"] == "Esha Employee"

    intern_id = next(item["id"] for item in task_options.json()["interns"] if item["name"] == "Ishan Intern")
    intern_task = client.post("/api/tasks", json={
        "task_title": "Intern-selected Delivery Task",
        "project_id": project_id,
        "assigned_user_id": intern_id,
    })
    assert intern_task.status_code == 201
    assert intern_task.json()["assigned_user_id"] == intern_id
    assert intern_task.json()["assigned_user_name"] == "Ishan Intern"

    with TestingSession() as db:
        unrelated_intern_id = db.query(User.id).filter(User.email == "intern2@example.com").scalar()
    unauthorized_task = client.post("/api/tasks", json={
        "task_title": "Unrelated intern task",
        "project_id": project_id,
        "assigned_user_id": unrelated_intern_id,
    })
    assert unauthorized_task.status_code == 403
    assert unauthorized_task.json()["detail"] == "You can only assign tasks to interns assigned to you."

    assert "Persistent Delivery Project" in {item["project_name"] for item in client.get("/api/projects").json()}
    assert "Persistent Delivery Task" in {item["task_title"] for item in client.get("/api/tasks").json()}
    employee_dashboard = client.get("/api/dashboard").json()
    assert employee_dashboard["metrics"]["projects"] == 2
    assert employee_dashboard["metrics"]["active_projects"] == 2
    assert employee_dashboard["metrics"]["open_tasks"] == 5
    assert any(item["project_name"] == "Persistent Delivery Project" for item in employee_dashboard["projects"])
    persisted_task = next(item for item in employee_dashboard["tasks"] if item["task_title"] == "Persistent Delivery Task")
    assert persisted_task["project_name"] == "Persistent Delivery Project"
    assert persisted_task["assigned_user_name"] == "Esha Employee"

    assert login("management@example.com").status_code == 200
    assert "Persistent Delivery Project" in {item["project_name"] for item in client.get("/api/projects").json()}
    assert "Persistent Delivery Task" in {item["task_title"] for item in client.get("/api/tasks").json()}
    management_dashboard = client.get("/api/dashboard").json()
    assert management_dashboard["metrics"]["total_projects"] == 4
    assert management_dashboard["metrics"]["total_tasks"] == 8
    assert client.get("/api/projects/options").status_code == 403
    assert client.get("/api/tasks/options").status_code == 403
    assert client.post("/api/projects", json={"project_name": "Forbidden"}).status_code == 403
    assert client.post("/api/tasks", json={"task_title": "Forbidden"}).status_code == 403
    assert client.patch(f"/api/tasks/{task.json()['id']}", json={"status": "Completed"}).status_code == 403
    assert client.patch(f"/api/tasks/{task.json()['id']}/submission", json={"progress_note": "Forbidden"}).status_code == 403

    assert login("employee@example.com").status_code == 200
    assert "Persistent Delivery Project" in {item["project_name"] for item in client.get("/api/projects").json()}
    assert "Persistent Delivery Task" in {item["task_title"] for item in client.get("/api/tasks").json()}


def test_create_endpoints_reject_invalid_relationships():
    seed_rbac_workspace()
    assert login("employee@example.com").status_code == 200
    assert client.post("/api/projects", json={
        "project_name": "Invalid owner",
        "responsible_employee_id": 999999,
    }).status_code == 400
    assert client.post("/api/tasks", json={
        "task_title": "Invalid project",
        "project_id": 999999,
    }).status_code == 400


def test_employee_can_update_and_delete_an_owned_project_and_management_cannot_mutate_projects():
    seed_rbac_workspace()
    assert login("employee@example.com").status_code == 200

    created = client.post("/api/projects", json={
        "project_name": "Editable Project",
        "project_category": "Platform",
        "current_status": "Planning",
        "progress_percentage": 5,
    })
    assert created.status_code == 201
    project_id = created.json()["id"]

    updated = client.patch(f"/api/projects/{project_id}", json={
        "project_name": "Updated Project",
        "project_category": "Operations",
        "project_description": "Updated and persisted",
        "current_status": "Active",
        "progress_percentage": 60,
        "target_date": "2031-03-20",
    })
    assert updated.status_code == 200
    assert updated.json()["project_name"] == "Updated Project"
    assert updated.json()["progress_percentage"] == "60.00"
    persisted = next(item for item in client.get("/api/projects").json() if item["id"] == project_id)
    assert persisted["project_description"] == "Updated and persisted"

    assert login("management@example.com").status_code == 200
    assert client.post("/api/projects", json={"project_name": "Forbidden"}).status_code == 403
    assert client.patch(f"/api/projects/{project_id}", json={"project_name": "Forbidden"}).status_code == 403
    assert client.delete(f"/api/projects/{project_id}").status_code == 403

    assert login("employee@example.com").status_code == 200
    deleted = client.delete(f"/api/projects/{project_id}")
    assert deleted.status_code == 204
    assert all(item["id"] != project_id for item in client.get("/api/projects").json())


def test_project_deletion_is_blocked_when_related_records_would_be_lost():
    seed_rbac_workspace()
    assert login("employee@example.com").status_code == 200
    owned_project = next(item for item in client.get("/api/projects").json() if item["project_name"] == "Assigned Project")

    response = client.delete(f"/api/projects/{owned_project['id']}")

    assert response.status_code == 409
    assert "task(s)" in response.json()["detail"]
    assert any(item["id"] == owned_project["id"] for item in client.get("/api/projects").json())


def test_management_has_read_only_access_to_meetings_and_rooms():
    seed_rbac_workspace()
    assert login("management@example.com").status_code == 200

    assert client.get("/api/meetings").status_code == 200
    assert client.get("/api/meetings/options").status_code == 200
    assert client.get("/api/meeting-rooms").status_code == 200
    assert client.get("/api/meeting-rooms/calendar").status_code == 200

    meeting_payload = {
        "meeting_title": "Forbidden meeting",
        "start_datetime": "2032-01-10T09:00:00",
        "end_datetime": "2032-01-10T10:00:00",
    }
    room_payload = {"room_name": "Forbidden room"}

    assert client.post("/api/meetings", json=meeting_payload).status_code == 403
    assert client.put("/api/meetings/1", json=meeting_payload).status_code == 403
    assert client.delete("/api/meetings/1").status_code == 403
    assert client.post("/api/meeting-rooms", json=room_payload).status_code == 403
    assert client.put("/api/meeting-rooms/1", json=room_payload).status_code == 403
    assert client.delete("/api/meeting-rooms/1").status_code == 403


def test_intern_supervisor_registration_rules_and_response_details():
    employee = register({
        "name": "Active Supervisor",
        "email": "supervisor@example.com",
        "password": "Password123",
        "role": "employee",
        "designation": "Engineer",
        "department": "Digital Lab",
    })
    assert employee.status_code == 201
    supervisor_id = employee.json()["user"]["id"]

    options = client.get("/api/auth/supervisors")
    assert options.status_code == 200
    assert options.json() == [{"id": supervisor_id, "name": "Active Supervisor"}]

    assigned = register({
        "name": "Assigned Intern",
        "email": "assigned@example.com",
        "password": "Password123",
        "role": "intern",
        "assigned_supervisor_id": supervisor_id,
    })
    assert assigned.status_code == 201
    assert assigned.json()["user"]["assigned_supervisor_id"] == supervisor_id
    assert assigned.json()["user"]["assigned_supervisor_name"] == "Active Supervisor"

    unassigned = register({
        "name": "Unassigned Intern",
        "email": "unassigned@example.com",
        "password": "Password123",
        "role": "intern",
        "assigned_supervisor_id": None,
    })
    assert unassigned.status_code == 201
    assert unassigned.json()["user"]["assigned_supervisor_id"] is None

    with TestingSession() as db:
        assert db.query(User).filter(User.email == "unassigned@example.com").one().assigned_supervisor_id is None
        assert db.query(User).filter(User.email == "supervisor@example.com").one().assigned_supervisor_id is None


def test_registration_rejects_non_employee_invalid_and_non_intern_supervisors():
    intern = register({"name": "Other Intern", "email": "other@example.com", "password": "Password123", "role": "intern"})
    manager = register({
        "name": "Manager", "email": "manager@example.com", "password": "Password123", "role": "management",
        "designation": "Manager", "department": "Digital Lab",
    })
    assert intern.status_code == 201
    assert manager.status_code == 201

    for index, supervisor_id in enumerate((intern.json()["user"]["id"], manager.json()["user"]["id"], 999999)):
        response = register({
            "name": f"Invalid Assignment {index}",
            "email": f"invalid-assignment-{index}@example.com",
            "password": "Password123",
            "role": "intern",
            "assigned_supervisor_id": supervisor_id,
        })
        assert response.status_code == 400

    non_intern = register({
        "name": "Invalid Employee", "email": "invalid-employee@example.com", "password": "Password123",
        "role": "employee", "designation": "Engineer", "department": "Digital Lab",
        "assigned_supervisor_id": intern.json()["user"]["id"],
    })
    assert non_intern.status_code == 422


def test_management_updates_supervisors_and_role_change_clears_assignments():
    supervisor = register({
        "name": "Supervisor", "email": "supervisor@example.com", "password": "Password123", "role": "employee",
        "designation": "Engineer", "department": "Digital Lab",
    }).json()["user"]
    intern = register({"name": "Intern", "email": "intern@example.com", "password": "Password123", "role": "intern"}).json()["user"]
    register({
        "name": "Manager", "email": "manager@example.com", "password": "Password123", "role": "management",
        "designation": "Manager", "department": "Digital Lab",
    })
    assert login("manager@example.com").status_code == 200

    assigned = client.patch(f"/api/users/{intern['id']}", json={"assigned_supervisor_id": supervisor["id"]})
    assert assigned.status_code == 200
    assert assigned.json()["assigned_supervisor_name"] == "Supervisor"
    assert client.patch(f"/api/users/{intern['id']}", json={"assigned_supervisor_id": intern["id"]}).status_code == 400

    role_change = client.patch(f"/api/users/{supervisor['id']}", json={"role": "management"})
    assert role_change.status_code == 200
    users = client.get("/api/users").json()
    updated_intern = next(user for user in users if user["id"] == intern["id"])
    assert updated_intern["assigned_supervisor_id"] is None
    assert updated_intern["assigned_supervisor_name"] is None
# End of test module.
