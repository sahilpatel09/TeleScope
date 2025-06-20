import os
import random
import time
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.tracing_config import configure_opentelemetry, traced

DATABASE_URL = "sqlite:///./sql_app.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="APM Demo API")

tracer = configure_opentelemetry(
    app=app,
    engine=engine,
    service_name="APM Demo with FastAPI",
    otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
)

@app.get("/")
@traced(span_name="root_endpoint")
async def root():
    # Custom spans for more granular control
    with tracer.start_as_current_span("getting service info"):
        time.sleep(0.4)

    with tracer.start_as_current_span("Processing welcome message"):
        time.sleep(0.1)

    return {"message": "Welcome to the APM Demo API with OpenTelemetry Tracing!"}


@app.post("/items/")
@traced(
    attributes={"operation.type": "create_item"}
)
async def create_item(
    name: str, description: Optional[str] = None, db: Session = Depends(get_db)
):
    """
    Creates a new item in the database.
    """
    with tracer.start_as_current_span("validate_item_info"):
        time.sleep(random.uniform(0.05, 0.2))

    new_item = Item(name=name, description=description)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@app.get("/items/{item_id}")
@traced()
async def read_item(item_id: int, db: Session = Depends(get_db)):
    """
    Retrieves an item by its ID.
    """
    item = db.query(Item).filter(Item.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.get("/items/")
@traced(span_name="retrieve_all_items_paginated")
async def read_all_items(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """
    Retrieves a list of items from the database with pagination.
    """
    items = db.query(Item).offset(skip).limit(limit).all()
    return items


@app.get("/complex_operation/")
@traced(
    attributes={"api.route": "/complex_operation"}
)
async def complex_operation(db: Session = Depends(get_db)):
    with tracer.start_as_current_span("fetch_some_data_first"):
        first_item = db.query(Item).first()
        time.sleep(0.01)

    with tracer.start_as_current_span("intermediate_calculation"):
        time.sleep(random.uniform(0.1, 0.3))

    with tracer.start_as_current_span("fetch_more_data_later"):
        second_item = db.query(Item).offset(random.randint(0, 10)).limit(1).first()
        time.sleep(0.01)

    if not first_item and not second_item:
        new_item_name = f"AutoItem_{int(time.time())}_{random.randint(100, 999)}"
        new_item_desc = "Created by complex operation due to no existing items."
        with tracer.start_as_current_span("create_missing_item_if_needed"):
            new_item = Item(name=new_item_name, description=new_item_desc)
            db.add(new_item)
            db.commit()
            db.refresh(new_item)
            return {
                "message": "Performed complex operation and created a new item.",
                "new_item": new_item.name,
            }
    else:
        return {
            "message": "Performed complex operation.",
            "first_item_name": first_item.name if first_item else "None",
            "second_item_name": second_item.name if second_item else "None",
        }
