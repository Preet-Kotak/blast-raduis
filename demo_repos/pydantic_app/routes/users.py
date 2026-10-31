"""User API routes."""
from fastapi import APIRouter, HTTPException
from models.user import UserCreate, UserResponse
from services import user_service

router = APIRouter(tags=["users"])


@router.post("/", response_model=UserResponse)
def create_user(payload: UserCreate):
    return user_service.create(payload)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    user = user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
