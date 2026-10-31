"""User business logic."""
from models.user import UserCreate, UserResponse
from utils import validation

_store: dict = {}
_counter = 0


def create(payload: UserCreate) -> UserResponse:
    global _counter
    validation.check_unique_email(payload.email, list(_store.values()))
    _counter += 1
    user = UserResponse(
        id=_counter,
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
    )
    _store[_counter] = user
    return user


def get_by_id(user_id: int) -> UserResponse | None:
    return _store.get(user_id)
