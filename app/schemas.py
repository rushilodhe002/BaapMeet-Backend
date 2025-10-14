from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


# Auth
class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    message: str
    token: str
    user: Optional[UserOut] = None


# User
class ProfileResponse(UserOut):
    pass


# Meeting
class MeetingCreateRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)


class MeetingCreateResponse(BaseModel):
    meeting_id: str
    join_url: str


class MeetingJoinRequest(BaseModel):
    meeting_id: str


class ParticipantInfo(BaseModel):
    id: int
    name: str


class MeetingJoinResponse(BaseModel):
    message: str
    participants: List[ParticipantInfo]
    host_id: int


class MeetingEndRequest(BaseModel):
    meeting_id: str


class MessageResponse(BaseModel):
    message: str


# Chat
class ChatMessageOut(BaseModel):
    id: int
    user_id: int
    name: str
    message: str
    timestamp: datetime

    class Config:
        from_attributes = True


# TURN
class IceServer(BaseModel):
    urls: List[str]
    username: Optional[str] = None
    credential: Optional[str] = None


class TurnConfigResponse(BaseModel):
    iceServers: List[IceServer]


# Logs
class MeetingLog(BaseModel):
    meeting_id: str
    host: str
    started_at: datetime
    ended_at: Optional[datetime]
    participants: int
