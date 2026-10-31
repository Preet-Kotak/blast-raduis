"""Item data models using pydantic v1."""
from pydantic import BaseModel, validator, ConstrainedStr, ConstrainedInt
from typing import Optional

# ConstrainedStr and ConstrainedInt removed in pydantic v2
ItemName = ConstrainedStr(min_length=1, max_length=100)
ItemPrice = ConstrainedInt(ge=0)


class ItemCreate(BaseModel):
    name: ItemName
    price: ItemPrice
    description: Optional[str] = None
    quantity: int = 0

    # validator removed in pydantic v2 — use field_validator
    @validator("quantity")
    def quantity_non_negative(cls, v):
        if v < 0:
            raise ValueError("Quantity cannot be negative")
        return v

    @validator("name")
    def name_stripped(cls, v):
        return v.strip()


class ItemResponse(BaseModel):
    id: int
    name: str
    price: int
    description: Optional[str]
    quantity: int

    class Config:
        orm_mode = True
