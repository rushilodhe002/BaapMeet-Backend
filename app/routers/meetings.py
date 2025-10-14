from datetime import datetime
from typing import List
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Meeting, Participant, User, ChatMessage
from ..schemas import (
    MeetingCreateRequest,
    MeetingCreateResponse,
    MeetingJoinRequest,
    MeetingJoinResponse,
    ParticipantInfo,
    MeetingEndRequest,
    MessageResponse,
    ChatMessageOut,
)
from ..ws import manager


router = APIRouter(prefix="/meeting", tags=["Meeting"])


def _generate_meet_code() -> str:
    letters = string.ascii_lowercase
    part1 = ''.join(secrets.choice(letters) for _ in range(3))
    part2 = ''.join(secrets.choice(letters) for _ in range(4))
    part3 = ''.join(secrets.choice(letters) for _ in range(3))
    return f"{part1}-{part2}-{part3}"


@router.post("/create", response_model=MeetingCreateResponse)
def create_meeting(
    payload: MeetingCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Generate a Google Meet-style code (e.g., nwy-rykv-gbd), ensure uniqueness
    code = _generate_meet_code()
    while db.query(Meeting).filter(Meeting.meeting_id == code).first() is not None:
        code = _generate_meet_code()

    meeting = Meeting(host_id=current_user.id, meeting_id=code)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    # Return a Meet-like URL (frontend can choose to use this directly)
    join_url = f"https://meet.google.com/{meeting.meeting_id}"
    return MeetingCreateResponse(meeting_id=meeting.meeting_id, join_url=join_url)


@router.post("/join", response_model=MeetingJoinResponse)
def join_meeting(
    payload: MeetingJoinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting: Meeting | None = (
        db.query(Meeting).filter(Meeting.meeting_id == str(payload.meeting_id)).first()
    )
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.ended_at is not None:
        raise HTTPException(status_code=400, detail="Meeting already ended")

    # Check if already joined and not left
    participant = (
        db.query(Participant)
        .filter(Participant.meeting_id == payload.meeting_id, Participant.user_id == current_user.id, Participant.left_at.is_(None))
        .first()
    )
    if not participant:
        participant = Participant(meeting_id=payload.meeting_id, user_id=current_user.id)
        db.add(participant)
        db.commit()

    # Participants list
    joins: List[Participant] = (
        db.query(Participant).filter(Participant.meeting_id == str(payload.meeting_id), Participant.left_at.is_(None)).all()
    )
    participants = []
    for j in joins:
        u = db.get(User, j.user_id)
        participants.append(ParticipantInfo(id=j.user_id, name=u.name if u else "User"))

    return MeetingJoinResponse(message="Joined successfully", participants=participants, host_id=meeting.host_id)


@router.post("/end", response_model=MessageResponse)
async def end_meeting(
    payload: MeetingEndRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting: Meeting | None = (
        db.query(Meeting).filter(Meeting.meeting_id == str(payload.meeting_id)).first()
    )
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.host_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only host can end the meeting")

    if meeting.ended_at is None:
        meeting.ended_at = datetime.utcnow()
        # mark active participants as left
        db.query(Participant).filter(
            Participant.meeting_id == payload.meeting_id, Participant.left_at.is_(None)
        ).update({Participant.left_at: datetime.utcnow()})
        db.commit()
        # broadcast meeting ended over websockets
        try:
            await manager.broadcast(str(meeting.meeting_id), {"type": "meeting-ended"})
        except Exception:
            pass

    return MessageResponse(message="Meeting ended successfully")


@router.get("/{meeting_id}/participants", response_model=list[ParticipantInfo])
def list_participants(meeting_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    meeting = db.query(Meeting).filter(Meeting.meeting_id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    joins = (
        db.query(Participant).filter(Participant.meeting_id == meeting_id, Participant.left_at.is_(None)).all()
    )
    return [ParticipantInfo(id=j.user_id, name=(db.get(User, j.user_id)).name) for j in joins]


@router.get("/{meeting_id}/chat", response_model=list[ChatMessageOut])
def get_chat_history(meeting_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    meeting = db.query(Meeting).filter(Meeting.meeting_id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.meeting_id == meeting_id)
        .order_by(ChatMessage.timestamp.asc())
        .all()
    )
    result: list[ChatMessageOut] = []
    for m in msgs:
        u = db.get(User, m.user_id)
        result.append(ChatMessageOut(id=m.id, user_id=m.user_id, name=u.name if u else "Unknown", message=m.message, timestamp=m.timestamp))
    return result
