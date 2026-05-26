# Stock Management API

A small FastAPI service for managing products, warehouses, and stock levels.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

The API is then available at http://localhost:8000, with interactive docs at
http://localhost:8000/docs.

Two warehouses (`Paris warehouse`, `Lyon warehouse`) are seeded automatically
on first run.

## Endpoints

- `POST /products` — create a product
- `GET /products` — list products with total stock across all warehouses
- `GET /products/low-stock` — list products whose total stock is below the
  reorder threshold
- `POST /stocks/adjustments` — record a stock movement (positive to add,
  negative to remove)

## Project layout

```
app/
├── main.py        # FastAPI app, table creation, warehouse seeding
├── database.py    # SQLAlchemy engine, session, get_db dependency
├── models.py      # SQLAlchemy ORM models
├── schemas.py     # Pydantic request/response schemas
├── services.py    # Business logic (ProductService, StockService)
└── routers.py     # HTTP endpoints
```
