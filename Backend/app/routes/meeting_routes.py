from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.meeting_schema import MeetingAttendanceUpdate, MeetingCreate, MeetingOptionsResponse, MeetingResponse, MeetingUpdate
from ..services import meeting_service
from ..utils.permissions import require_roles


router = APIRouter(prefix="/api/meetings", tags=["meetings"])
calendar_viewer = require_roles("intern", "employee", "management")
employee_or_management = require_roles("employee", "management")
employee_only = require_roles("employee")
intern_only = require_roles("intern")


@router.get("", response_model=list[MeetingResponse])
def list_meetings(user=Depends(calendar_viewer), db: Session = Depends(get_db)):
    return meeting_service.list_meetings(db, user)


@router.get("/options", response_model=MeetingOptionsResponse)
def meeting_options(user=Depends(employee_or_management), db: Session = Depends(get_db)):
    return meeting_service.meeting_options(db, user)


@router.patch("/{meeting_id}/attendance", response_model=MeetingResponse)
def update_attendance(meeting_id: int, payload: MeetingAttendanceUpdate, user=Depends(intern_only), db: Session = Depends(get_db)):
    return meeting_service.update_attendance(db, meeting_id, user, payload.attendance_status)


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
def create_meeting(payload: MeetingCreate, user=Depends(employee_only), db: Session = Depends(get_db)):
    return meeting_service.create_meeting(db, payload, user.id)


@router.put("/{meeting_id}", response_model=MeetingResponse)
def update_meeting(meeting_id: int, payload: MeetingUpdate, user=Depends(employee_only), db: Session = Depends(get_db)):
    return meeting_service.update_meeting(db, meeting_id, payload, user)


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(meeting_id: int, user=Depends(employee_or_management), db: Session = Depends(get_db)):
    meeting_service.delete_meeting(db, meeting_id, user)
