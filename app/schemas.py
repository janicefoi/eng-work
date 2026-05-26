from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    unit_price: float = Field(gt=0)
    reorder_threshold: int = 0


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    unit_price: float
    reorder_threshold: int


class ProductReadWithStock(ProductRead):
    total_stock: int
    is_low_stock: bool


class StockAdjustment(BaseModel):
    product_id: int
    warehouse_id: int
    quantity_change: int = Field(description="Positive to add, negative to remove")
    reason: str = Field(min_length=1, max_length=200)


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    warehouse_id: int
    quantity_change: int
    reason: str
    created_at: datetime
