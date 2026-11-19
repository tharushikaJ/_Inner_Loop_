from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models.meeting import Meeting, MeetingAttendee, MeetingProject
from ..models.project import Project
from ..models.room import MeetingRoom
from ..models.user import User
from ..schemas.meeting_schema import MeetingCreate, MeetingUpdate


def meeting_data(db: Session, meeting: Meeting, current_user: User | None = None) -> dict:
	attendees = db.query(MeetingAttendee).filter(MeetingAttendee.meeting_id == meeting.id).all()
	current_attendee = next((row for row in attendees if current_user and row.user_id == current_user.id), None)
	return {
		"id": meeting.id,
		"meeting_title": meeting.meeting_title,
		"meeting_type": meeting.meeting_type,
		"start_datetime": meeting.start_datetime,
		"end_datetime": meeting.end_datetime,
		"meeting_room_id": meeting.meeting_room_id,
		"status": meeting.status,
		"meeting_minutes": meeting.meeting_minutes,
		"created_by": meeting.created_by,
		"attendee_user_ids": [row.user_id for row in attendees],
		"accepted_attendee_count": sum(1 for row in attendees if (row.attendance_status or "").lower() == "accepted"),
		"current_user_attendance_status": current_attendee.attendance_status if current_attendee else None,
		"project_ids": [row.project_id for row in db.query(MeetingProject).filter(MeetingProject.meeting_id == meeting.id).all()],
	}


def list_meetings(db: Session, user: User) -> list[dict]:
	query = db.query(Meeting)
	if user.role == "intern":
		query = query.join(MeetingAttendee, MeetingAttendee.meeting_id == Meeting.id).filter(MeetingAttendee.user_id == user.id)
	meetings = query.order_by(Meeting.start_datetime.asc()).all()
	return [meeting_data(db, meeting, user) for meeting in meetings]


def meeting_options(db: Session, user: User) -> dict:
	attendee_query = db.query(User).filter(User.status == "active")
	if user.role == "employee":
		attendee_query = attendee_query.filter(
			User.role == "intern",
			User.assigned_supervisor_id == user.id,
		)
	return {
		"attendees": [
			{"id": user.id, "name": user.name, "email": user.email, "role": user.role}
			for user in attendee_query.order_by(User.name.asc()).all()
		],
		"projects": [
			{"id": project.id, "project_name": project.project_name}
			for project in db.query(Project).order_by(Project.project_name.asc()).all()
		],
		"rooms": [
			{"id": room.id, "room_name": room.room_name, "location": room.location}
			for room in db.query(MeetingRoom).order_by(MeetingRoom.room_name.asc()).all()
		],
	}


def _save_links(db: Session, meeting_id: int, attendee_user_ids: list[int], project_ids: list[int]) -> None:
	requested_attendee_ids = set(attendee_user_ids)
	existing_attendees = db.query(MeetingAttendee).filter(MeetingAttendee.meeting_id == meeting_id).all()
	existing_attendee_ids = {row.user_id for row in existing_attendees}
	for attendee in existing_attendees:
		if attendee.user_id not in requested_attendee_ids:
			db.delete(attendee)
	db.query(MeetingProject).filter(MeetingProject.meeting_id == meeting_id).delete()
	db.add_all([MeetingAttendee(meeting_id=meeting_id, user_id=user_id, attendance_status="Invited") for user_id in requested_attendee_ids - existing_attendee_ids])
	db.add_all([MeetingProject(meeting_id=meeting_id, project_id=project_id) for project_id in set(project_ids)])


def update_attendance(db: Session, meeting_id: int, user: User, attendance_status: str) -> dict:
	meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
	if not meeting:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
	attendee = db.query(MeetingAttendee).filter(
		MeetingAttendee.meeting_id == meeting_id,
		MeetingAttendee.user_id == user.id,
	).first()
	if not attendee:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not invited to this meeting")
	attendee.attendance_status = attendance_status
	db.commit()
	return meeting_data(db, meeting, user)


def _ensure_room_available(db: Session, room_id: int | None, start_datetime, end_datetime, exclude_meeting_id: int | None = None) -> None:
	if room_id is None:
		return
	room = db.query(MeetingRoom).filter(MeetingRoom.id == room_id).first()
	if not room:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The selected meeting room does not exist")
	if (room.status or "").lower() != "available":
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The selected meeting room is not available")
	query = db.query(Meeting).filter(
		Meeting.meeting_room_id == room_id,
		Meeting.start_datetime < end_datetime,
		Meeting.end_datetime > start_datetime,
		Meeting.status != "Cancelled",
	)
	if exclude_meeting_id is not None:
		query = query.filter(Meeting.id != exclude_meeting_id)
	if query.first():
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This room is already booked during the selected meeting time")


def create_meeting(db: Session, payload: MeetingCreate, created_by: int) -> dict:
	_ensure_room_available(db, payload.meeting_room_id, payload.start_datetime, payload.end_datetime)
	meeting = Meeting(**payload.model_dump(exclude={"attendee_user_ids", "project_ids"}), created_by=created_by)
	db.add(meeting)
	try:
		db.flush()
		_save_links(db, meeting.id, payload.attendee_user_ids, payload.project_ids)
		db.commit()
	except IntegrityError as error:
		db.rollback()
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more selected attendees, projects, or rooms do not exist") from error
	db.refresh(meeting)
	return meeting_data(db, meeting)


def _can_manage_meeting(meeting: Meeting, user: User) -> bool:
	return user.role == "management" or meeting.created_by == user.id


def update_meeting(db: Session, meeting_id: int, payload: MeetingUpdate, user: User) -> dict:
	meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
	if not meeting:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
	if not _can_manage_meeting(meeting, user):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update meetings you created")
	_ensure_room_available(db, payload.meeting_room_id, payload.start_datetime, payload.end_datetime, meeting_id)
	for field, value in payload.model_dump(exclude={"attendee_user_ids", "project_ids"}).items():
		setattr(meeting, field, value)
	try:
		_save_links(db, meeting.id, payload.attendee_user_ids, payload.project_ids)
		db.commit()
	except IntegrityError as error:
		db.rollback()
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more selected attendees, projects, or rooms do not exist") from error
	db.refresh(meeting)
	return meeting_data(db, meeting)


def delete_meeting(db: Session, meeting_id: int, user: User) -> None:
	meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
	if not meeting:
		if user.role == "management":
			raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Management has read-only meeting access")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
	if not _can_manage_meeting(meeting, user):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete meetings you created")
	db.delete(meeting)
	db.commit()
