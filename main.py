import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from jsonlog import get_logger

app = FastAPI(title="shop-api")
logger = get_logger()


@app.middleware("http")
async def log_unhandled_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.error(
            f"{request.method} {request.url.path} failed: {type(exc).__name__}: {exc}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=500, content={"detail": "Internal Server Error"}
        )


# ---- "Database": plain Python dicts ----
PRODUCTS = {
    1: {"name": "Wireless Mouse", "cost": 799},
    2: {"name": "Mechanical Keyboard", "cost": 3499},
    3: {"name": "USB-C Hub", "cost": 1899},
}

CART: list[dict] = []


class CartItem(BaseModel):
    product_id: int
    quantity: int = 1


@app.get("/health")
def health():
    return {"status": "ok", "service": "shop-api"}


@app.get("/products")
def list_products():
    return [{"id": pid, **data} for pid, data in PRODUCTS.items()]


@app.get("/products/{product_id}")
def get_product(product_id: int):
    if product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"id": product_id, **PRODUCTS[product_id]}


@app.get("/cart")
def view_cart():
    return {"items": CART}


@app.post("/cart")
def add_to_cart(item: CartItem):
    if item.product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")
    CART.append({"product_id": item.product_id, "quantity": item.quantity})
    return {"items": CART}


@app.post("/checkout")
def checkout():
    if not CART:
        raise HTTPException(status_code=400, detail="Cart is empty")

    total = 0
    for item in CART:
        price = PRODUCTS[item["product_id"]]["price"]
        total += price * item["quantity"]

    CART.clear()
    return {"status": "paid", "total": total}
# ---- Dashboard ----
BASE_DIR = Path(__file__).parent


def incidents_db_path() -> Path:
    default = BASE_DIR.parent / "incident-agent" / "incidents.db"
    return Path(os.environ.get("INCIDENTS_DB", default))


@app.get("/api/incidents")
def api_incidents():
    path = incidents_db_path()
    if not path.exists():
        return []
    try:
        # mode=ro: this app can only READ Sam's database, never change it
        conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, timeout=2)
        conn.row_factory = sqlite3.Row
        try:
            rows = [dict(r) for r in conn.execute("SELECT * FROM incidents ORDER BY id DESC")]
        finally:
            conn.close()
    except sqlite3.Error:
        return []  # DB locked for a moment or table not created yet
    for r in rows:
        r.pop("report", None)  # the long write-up; keep the list light
    return rows


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(BASE_DIR / "dashboard.html")