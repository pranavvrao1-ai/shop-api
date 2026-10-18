import sys
import subprocess
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
        prod = PRODUCTS[item["product_id"]]
        price = prod["cost"]
        total += price * item["quantity"]

    CART.clear()
    return {"status": "paid", "total": total}


def _launch(script_name):
    """Run break.py or reset.py in a separate process, so the reply is sent
    before the file changes and the server restarts."""
    flags = 0
    if os.name == "nt":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [sys.executable, str(Path(__file__).parent / script_name)],
        cwd=str(Path(__file__).parent),
        creationflags=flags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@app.post("/api/demo/break")
def demo_break():
    _launch("break.py")
    return {"status": "breaking", "message": "Committing the bug to the repository. Checkout will start failing in a few seconds."}


@app.post("/api/demo/reset")
def demo_reset():
    _launch("reset.py")
    return {"status": "healing", "message": "Restoring the healthy code. Checkout will recover in a few seconds."}


# ---- Dashboard ----
BASE_DIR = Path(__file__).parent


def incidents_db_path() -> Path:
    env = os.environ.get("INCIDENTS_DB")
    if env:
        return Path(env)
    for candidate in [
        BASE_DIR.parent / "ai on call engineer" / "incidents.db",
        BASE_DIR.parent / "incident-agent" / "incidents.db",
        BASE_DIR / "incidents.db",
    ]:
        if candidate.exists():
            return candidate
    return BASE_DIR.parent / "incident-agent" / "incidents.db"


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
    return rows


@app.get("/", include_in_schema=False)
@app.get("/store", include_in_schema=False)
def store():
    return FileResponse(BASE_DIR / "store.html")


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(BASE_DIR / "dashboard.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
