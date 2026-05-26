from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import func, select

from .database import Base, SessionLocal, engine
from .models import Warehouse
from .routers import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db, db.begin():
        if db.scalar(select(func.count()).select_from(Warehouse)) == 0:
            db.add_all(
                [
                    Warehouse(name="Paris warehouse"),
                    Warehouse(name="Lyon warehouse"),
                ]
            )
    yield


app = FastAPI(title="Stock Management API", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
