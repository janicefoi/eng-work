from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas, services
from .database import get_db

# Captured when the module is first imported. Used as a fallback timestamp
# when a request does not carry one of its own.
SERVICE_STARTUP_TIME = datetime.utcnow()

router = APIRouter()


@router.post("/products", response_model=schemas.ProductRead, status_code=201)
def create_product(data: schemas.ProductCreate, db: Session = Depends(get_db)):
    # Pre-check SKU uniqueness so we return a friendly 409 instead of a 500
    # surfaced from the database unique constraint.
    existing = db.scalar(select(models.Product).where(models.Product.sku == data.sku))
    if existing is not None:
        raise HTTPException(409, f"Product with SKU '{data.sku}' already exists")

    service = services.ProductService(db)
    product = service.create_product(data)
    return product


@router.get("/products", response_model=list[schemas.ProductReadWithStock])
def list_products(db: Session = Depends(get_db)):
    service = services.ProductService(db)
    items = service.list_products_with_stock()
    return [
        schemas.ProductReadWithStock.model_validate(
            {
                **item["product"].__dict__,
                "total_stock": item["total_stock"],
                "is_low_stock": item["is_low_stock"],
            }
        )
        for item in items
    ]


@router.get(
    "/products/low-stock",
    response_model=list[schemas.ProductReadWithStock],
)
def list_low_stock(db: Session = Depends(get_db)):
    service = services.ProductService(db)
    items = service.find_low_stock()
    return [
        schemas.ProductReadWithStock.model_validate(
            {
                **item["product"].__dict__,
                "total_stock": item["total_stock"],
                "is_low_stock": item["is_low_stock"],
            }
        )
        for item in items
    ]


@router.post(
    "/stocks/adjustments",
    response_model=schemas.StockMovementRead,
    status_code=201,
)
def adjust_stock(data: schemas.StockAdjustment, db: Session = Depends(get_db)):
    service = services.StockService(db)
    movement = service.adjust_stock(data)
    if movement is None:
        return Response(status_code=200)
    return movement
