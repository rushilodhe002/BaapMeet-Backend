import json
import asyncio
from typing import Dict, Set, Optional, DefaultDict
 
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
 
from .core import decode_token
from .database import get_db
from .models import Meeting, Participant, User, ChatMessage
 
 
router = APIRouter(prefix="/ws/meetings", tags=["WebSocket"])
 
 
class Connection:
    def __init__(self, websocket: WebSocket, user_id: int, name: str):
        self.websocket = websocket
        self.user_id = user_id
        self.name = name
 
 
class RoomState:
    def __init__(self):
        self.presenter_id: Optional[int] = None
        self.media: Dict[int, Dict[str, bool]] = {}
 
 
class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Set[Connection]] = {}
        self.state: Dict[str, RoomState] = {}
        # meeting_id -> user_id -> set(connections). Supports multiple tabs per user
        self.user_index: Dict[str, Dict[int, Set[Connection]]] = {}
 
    def room_key(self, meeting_id: str) -> str:
        return meeting_id
 
    def get_room(self, meeting_id: str) -> Set[Connection]:
        return self.rooms.setdefault(self.room_key(meeting_id), set())
 
    def get_state(self, meeting_id: str) -> RoomState:
        return self.state.setdefault(self.room_key(meeting_id), RoomState())
 
    def add(self, meeting_id: str, conn: Connection):
        room = self.get_room(meeting_id)
        room.add(conn)
        st = self.get_state(meeting_id)
        st.media.setdefault(conn.user_id, {"mic": True, "cam": True})
        # index
        user_map = self.user_index.setdefault(self.room_key(meeting_id), {})
        conns = user_map.setdefault(conn.user_id, set())
        conns.add(conn)
 
    def remove(self, meeting_id: str, conn: Connection):
        room = self.get_room(meeting_id)
        if conn in room:
            room.remove(conn)
            # index cleanup
            uidx = self.user_index.get(self.room_key(meeting_id))
            if uidx is not None:
                s = uidx.get(conn.user_id)
                if s is not None and conn in s:
                    s.remove(conn)
                    if not s:
                        uidx.pop(conn.user_id, None)
        if not room:
            self.rooms.pop(self.room_key(meeting_id), None)
            self.state.pop(self.room_key(meeting_id), None)
            self.user_index.pop(self.room_key(meeting_id), None)
 
    async def broadcast(self, meeting_id: str, message: dict, exclude: Connection | None = None):
        room = self.get_room(meeting_id)
        data = json.dumps(message)
        tasks = []
        for conn in list(room):
            if exclude and conn is exclude:
                continue
            tasks.append(self._safe_send(conn, data, meeting_id))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
 
    async def _safe_send(self, conn: Connection, data: str, meeting_id: str):
        try:
            await conn.websocket.send_text(data)
        except Exception:
            # drop broken connections
            self.remove(meeting_id, conn)
 
    async def send_to_user(self, meeting_id: str, user_id: int, message: dict):
        data = json.dumps(message)
        uidx = self.user_index.get(self.room_key(meeting_id), {})
        conns = list(uidx.get(user_id, set()))
        tasks = [self._safe_send(c, data, meeting_id) for c in conns]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
 
 
manager = RoomManager()
 
 
@router.websocket("/{meeting_id}")
async def websocket_endpoint(websocket: WebSocket, meeting_id: str, db: Session = Depends(get_db)):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        await websocket.close(code=4401)
        return
 
    user: User | None = db.get(User, int(payload["sub"]))
    if not user:
        await websocket.close(code=4403)
        return
 
    meeting: Meeting | None = db.query(Meeting).filter(Meeting.meeting_id == meeting_id).first()
    if not meeting or meeting.ended_at is not None:
        await websocket.close(code=4404)
        return
 
    await websocket.accept()
    conn = Connection(websocket, user.id, user.name)
    manager.add(meeting_id, conn)
 
    # Ensure participant exists (idempotent)
    p = (
        db.query(Participant)
        .filter(Participant.meeting_id == meeting.meeting_id, Participant.user_id == user.id, Participant.left_at.is_(None))
        .first()
    )
    if not p:
        db.add(Participant(meeting_id=meeting.meeting_id, user_id=user.id))
        db.commit()
 
    # Send snapshot to new connection
    st = manager.get_state(meeting_id)
    snapshot = [
        {"id": c.user_id, "name": c.name, **st.media.get(c.user_id, {"mic": True, "cam": True})}
        for c in manager.get_room(meeting_id)
    ]
    await websocket.send_text(
        json.dumps({
            "type": "room-state",
            "participants": snapshot,
            "presenter_id": st.presenter_id,
        })
    )
 
    # Notify others
    await manager.broadcast(meeting_id, {"type": "user-joined", "user": {"id": user.id, "name": user.name}}, exclude=conn)
 
    try:
        while True:
            text = await websocket.receive_text()
            try:
                msg = json.loads(text)
            except Exception:
                continue
 
            mtype = msg.get("type")
            payload = {
                "type": mtype,
                "sender": {"id": user.id, "name": user.name},
                "data": msg.get("data"),
            }
 
            # Screen share + media state updates
            if mtype == "screen-share-start":
                st.presenter_id = user.id
                await manager.broadcast(meeting_id, payload, exclude=conn)
            elif mtype == "screen-share-stop":
                if st.presenter_id == user.id:
                    st.presenter_id = None
                await manager.broadcast(meeting_id, payload, exclude=conn)
            elif mtype in {"mute", "unmute", "camera-on", "camera-off"}:
                media = manager.get_state(meeting_id).media.setdefault(user.id, {"mic": True, "cam": True})
                if mtype in {"mute", "unmute"}:
                    media["mic"] = (mtype == "unmute")
                else:
                    media["cam"] = (mtype == "camera-on")
                await manager.broadcast(
                    meeting_id,
                    {"type": "media", "sender": {"id": user.id, "name": user.name}, "data": media},
                    exclude=conn,
                )
            # Signaling relay (targeted when 'to' present)
            elif mtype in {"offer", "answer", "ice-candidate"}:
                target = None
                try:
                    target = int((msg.get("data") or {}).get("to"))
                except Exception:
                    target = None
                if target:
                    await manager.send_to_user(meeting_id, target, payload)
                else:
                    await manager.broadcast(meeting_id, payload, exclude=conn)
            elif mtype == "chat":
                text = (msg.get("data") or {}).get("text")
                if isinstance(text, str) and text.strip():
                    # persist
                    cm = ChatMessage(meeting_id=meeting.meeting_id, user_id=user.id, message=text.strip())
                    db.add(cm)
                    db.commit()
                    await manager.broadcast(
                        meeting_id,
                        {
                            "type": "chat",
                            "sender": {"id": user.id, "name": user.name},
                            "data": {"id": cm.id, "text": text, "timestamp": cm.timestamp.isoformat()},
                        },
                        exclude=conn,
                    )
            else:
                # ignore unknown
                pass
 
    except WebSocketDisconnect:
        pass
    finally:
        manager.remove(meeting_id, conn)
        # mark left
        from sqlalchemy import func
        db.query(Participant).filter(
            Participant.meeting_id == meeting_id, Participant.user_id == user.id, Participant.left_at.is_(None)
        ).update({Participant.left_at: func.now()})
        db.commit()
        await manager.broadcast(meeting_id, {"type": "user-left", "user": {"id": user.id, "name": user.name}})
        # Do not auto-end meeting when host disconnects (e.g., on refresh).
        # Meetings should end explicitly via the /meeting/end endpoint.
 
 