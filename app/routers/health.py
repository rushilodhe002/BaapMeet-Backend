from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("/")
def health_check():
    """
    Health check endpoint to verify if the server is running.
    Returns status, message, and current server time.
    """
    return {
        "status": "ok",
        "message": "BaapMeet backend is healthy ✅",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

