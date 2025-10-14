from fastapi import APIRouter, Depends
from ..deps import get_current_user
from ..schemas import ProfileResponse
from ..models import User


router = APIRouter(prefix="/user", tags=["User"])


@router.get("/profile", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user

