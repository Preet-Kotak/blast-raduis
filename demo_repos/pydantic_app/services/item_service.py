"""Item business logic."""
from models.item import ItemCreate, ItemResponse
from utils import validation

_store: dict = {}
_counter = 0


def create(payload: ItemCreate) -> ItemResponse:
    global _counter
    validation.check_item_name(payload.name)
    _counter += 1
    item = ItemResponse(
        id=_counter,
        name=payload.name,
        price=payload.price,
        description=payload.description,
        quantity=payload.quantity,
    )
    _store[_counter] = item
    return item


def list_all() -> list:
    return list(_store.values())
