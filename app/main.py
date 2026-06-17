"""FastAPI microservice entrypoint.

Endpoints:
  GET  /                 -> service metadata (name, version, environment)
  GET  /health           -> liveness probe  (is the process alive?)
  GET  /ready            -> readiness probe (is it ready to serve traffic?)
  GET  /api/items        -> list all items
  POST /api/items        -> create a new item
  GET  /api/items/{id}   -> fetch a single item by id

Items are stored in memory for simplicity (the focus of this activity is
deployment/orchestration, not persistence).
"""
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.config import settings

# The FastAPI instance. title/version power the auto-generated docs at /docs.
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

# --- In-memory "database" -------------------------------------------------
_items: dict[int, dict] = {}
_next_id: int = 1


# --- Request/response models (validated automatically by FastAPI) ---------
class ItemIn(BaseModel):
    name: str
    description: Optional[str] = None


class ItemOut(ItemIn):
    id: int


# --- Metadata & probe endpoints -------------------------------------------
@app.get("/")
def root():
    """Returns who I am — handy to confirm which version/env is live."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }


@app.get("/health")
def health():
    """Liveness probe: if this fails, Kubernetes restarts the pod."""
    return {"status": "alive"}


@app.get("/ready")
def ready():
    """Readiness probe: if this fails, Kubernetes stops sending traffic."""
    return {"status": "ready"}


# --- Business endpoints ----------------------------------------------------
@app.get("/api/items", response_model=list[ItemOut])
def list_items():
    return [{"id": i, **data} for i, data in _items.items()]


@app.post("/api/items", response_model=ItemOut, status_code=201)
def create_item(item: ItemIn):
    global _next_id
    item_id = _next_id
    _items[item_id] = item.model_dump()
    _next_id += 1
    return {"id": item_id, **_items[item_id]}


@app.get("/api/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int):
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"id": item_id, **_items[item_id]}