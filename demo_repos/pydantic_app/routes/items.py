"""Item API routes."""
from fastapi import APIRouter
from models.item import ItemCreate, ItemResponse
from services import item_service

router = APIRouter(tags=["items"])


@router.post("/", response_model=ItemResponse)
def create_item(payload: ItemCreate):
    return item_service.create(payload)


@router.get("/")
def list_items():
    return item_service.list_all()
