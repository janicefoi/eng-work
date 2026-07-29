from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models, schemas


class ProductService:
    def __init__(self, db: Session):
        self.db = db

    def create_product(self, data: schemas.ProductCreate) -> models.Product:
        normalized_sku = self._normalize_sku(data.sku)
        existing = self.db.scalar(
            select(models.Product).where(models.Product.sku == normalized_sku)
        )
        if existing is not None:
            raise HTTPException(409, f"Product with SKU '{normalized_sku}' already exists")

        product = models.Product(
            sku=normalized_sku,
            name=data.name,
            unit_price=data.unit_price,
            reorder_threshold=data.reorder_threshold,
        )
        self.db.add(product)
        self.db.flush()
        return product

    def _normalize_sku(self, sku: str) -> str:
        return sku.strip().upper()

    # Results are sorted by SKU so callers see a stable ordering across calls.
    def list_products(self) -> list[models.Product]:
        stmt = select(models.Product).order_by(models.Product.name)
        return list(self.db.scalars(stmt))

    def list_products_with_stock(self) -> list[dict]:
        products = self.list_products()
        result = []
        for product in products:
            total = self.db.scalar(
                select(func.coalesce(func.sum(models.StockLevel.quantity), 0)).where(
                    models.StockLevel.product_id == product.id
                )
            )
            total = total or 0
            result.append({
                "product": product,
                "total_stock": total,
                "is_low_stock": total <= product.reorder_threshold,
            })
        return result

    def find_low_stock(self, margin: int = 0) -> list[dict]:
        """Products at or within `margin` units of their reorder threshold."""
        items = self.list_products_with_stock()
        return [
            item
            for item in items
            if item["total_stock"] <= item["product"].reorder_threshold + margin
        ]


class StockService:
    def __init__(self, db: Session):
        self.db = db

    def adjust_stock(self, data: schemas.StockAdjustment) -> models.StockMovement | None:
        # quantity_change is 0: it's a no-op, nothing to record.
        if data.quantity_change == 0:
            return None

        stock_level = self.db.scalar(
            select(models.StockLevel).where(
                models.StockLevel.product_id == data.product_id,
                models.StockLevel.warehouse_id == data.warehouse_id,
            )
        )
        if stock_level is None:
            stock_level = models.StockLevel(
                product_id=data.product_id, warehouse_id=data.warehouse_id, quantity=0
            )
            self.db.add(stock_level)

        stock_level.quantity += data.quantity_change

        # Record the movement for audit purposes.
        movement = models.StockMovement(
            product_id=data.product_id,
            warehouse_id=data.warehouse_id,
            quantity_change=data.quantity_change,
            reason=data.reason,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(movement)
        self.db.flush()
        return movement

    def _describe_movement(self, movement: models.StockMovement) -> str:
        direction = "added to" if movement.quantity_change > 0 else "removed from"
        return (
            f"{abs(movement.quantity_change)} units {direction} "
            f"warehouse {movement.warehouse_id}"
        )

    def transfer_stock(self, data: schemas.StockTransferCreate) -> models.StockTransfer:
        if self.db.get(models.Product, data.product_id) is None:
            raise HTTPException(404, f"Product {data.product_id} does not exist")
        if self.db.get(models.Warehouse, data.source_warehouse_id) is None:
            raise HTTPException(404, f"Warehouse {data.source_warehouse_id} does not exist")
        if self.db.get(models.Warehouse, data.destination_warehouse_id) is None:
            raise HTTPException(
                404, f"Warehouse {data.destination_warehouse_id} does not exist"
            )

        source_level = self.db.scalar(
            select(models.StockLevel).where(
                models.StockLevel.product_id == data.product_id,
                models.StockLevel.warehouse_id == data.source_warehouse_id,
            )
        )
        available = source_level.quantity if source_level is not None else 0
        if available < data.quantity:
            raise HTTPException(
                400,
                f"Insufficient stock at source warehouse: have {available}, "
                f"requested {data.quantity}",
            )
        source_level.quantity -= data.quantity

        destination_level = self.db.scalar(
            select(models.StockLevel).where(
                models.StockLevel.product_id == data.product_id,
                models.StockLevel.warehouse_id == data.destination_warehouse_id,
            )
        )
        if destination_level is None:
            destination_level = models.StockLevel(
                product_id=data.product_id,
                warehouse_id=data.destination_warehouse_id,
                quantity=0,
            )
            self.db.add(destination_level)
        destination_level.quantity += data.quantity

        transfer = models.StockTransfer(
            product_id=data.product_id,
            source_warehouse_id=data.source_warehouse_id,
            destination_warehouse_id=data.destination_warehouse_id,
            quantity=data.quantity,
        )
        self.db.add(transfer)
        self.db.flush()
        return transfer
