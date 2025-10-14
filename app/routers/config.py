from fastapi import APIRouter
from ..schemas import TurnConfigResponse, IceServer


router = APIRouter(prefix="/config", tags=["Config"])


@router.get("/turn", response_model=TurnConfigResponse)
def get_turn_config():
    # Expanded ICE server list for better NAT traversal.
    # Make sure your COTURN is listening on these ports and transports.
    return TurnConfigResponse(
        iceServers=[
            # Public STUN fallback + your STUN
            IceServer(urls=[
                "stun:stun.l.google.com:19302",
                "stun:13.232.155.193:3478",
            ]),
            # TURN UDP/TCP and TLS (5349). Ensure COTURN enables these.
            IceServer(
                urls=[
                    "turn:13.232.155.193:3478?transport=udp",
                    "turn:13.232.155.193:3478?transport=tcp",
                    "turns:13.232.155.193:5349?transport=tcp",
                ],
                username="baap",
                credential="Baap@2025",
            ),
        ]
    )
