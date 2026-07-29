from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from . import schemas, services
from .database import get_db

router = APIRouter()


@router.post("/products", response_model=schemas.ProductRead, status_code=201)
def create_product(data: schemas.ProductCreate, db: Session = Depends(get_db)):
    service = services.ProductService(db)
    return service.create_product(data)


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
def list_low_stock(
    margin: int = Query(0, ge=0, description="Extra buffer above the reorder threshold"),
    db: Session = Depends(get_db),
):
    service = services.ProductService(db)
    items = service.find_low_stock(margin=margin)
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


@router.post(
    "/stocks/transfers",
    response_model=schemas.StockTransferRead,
    status_code=201,
)
def transfer_stock(data: schemas.StockTransferCreate, db: Session = Depends(get_db)):
    service = services.StockService(db)
    return service.transfer_stock(data)
