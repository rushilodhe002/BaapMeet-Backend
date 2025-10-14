from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Meeting, Participant, User
from ..schemas import MeetingLog


router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("/meetings", response_model=list[MeetingLog])
def get_meeting_logs(db: Session = Depends(get_db)):
    meetings = db.query(Meeting).all()
    logs: list[MeetingLog] = []
    for m in meetings:
        host = db.get(User, m.host_id)
        count = (
            db.query(func.count(Participant.id))
            .filter(Participant.meeting_id == m.meeting_id)
            .scalar()
            or 0
        )
        logs.append(
            MeetingLog(
                meeting_id=m.meeting_id,
                host=host.name if host else "Unknown",
                started_at=m.created_at,
                ended_at=m.ended_at,
                participants=int(count),
            )
        )
    return logs
