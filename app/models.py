from datetime import datetime
import uuid as uuidpkg
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    hosted_meetings = relationship("Meeting", back_populates="host")
    messages = relationship("ChatMessage", back_populates="user")


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    meeting_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuidpkg.uuid4()))
    host_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    host = relationship("User", back_populates="hosted_meetings")
    participants = relationship("Participant", back_populates="meeting", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="meeting", cascade="all, delete-orphan")


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.meeting_id"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    left_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    meeting = relationship("Meeting", back_populates="participants")
    user = relationship("User")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.meeting_id"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    meeting = relationship("Meeting", back_populates="messages")
    user = relationship("User", back_populates="messages")
