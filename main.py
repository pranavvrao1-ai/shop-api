import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from demo_tools import ctl
from jsonlog import DEFAULT_PATH, get_logger

BASE_DIR = Path(__file__).parent
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
    1: {"name": "Wireless Mouse", "price": 799},
    2: {"name": "Mechanical Keyboard", "price": 3499},
    3: {"name": "USB-C Hub", "price": 1899},
}

CART: list[dict] = []


class CartItem(BaseModel):
    product_id: int
    quantity: int = 1


def compute_total(items):
    total = 0
    for item in items:
        prod = PRODUCTS[item["product_id"]]
        price = prod["price"]
        total += price * item["quantity"]
    return total


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
    total = compute_total(CART)
    CART.clear()
    return {"status": "paid", "total": total}


# ---- Demo controls: Break / Reset commit to GitHub, Render redeploys ----
def _toggle(broken):
    try:
        commit = ctl.set_broken(broken)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"GitHub commit failed: {type(exc).__name__}: {exc}"
        )
    if commit is None:
        return {"status": "noop", "message": "GitHub main is already in that state."}
    what = "Bug committed" if broken else "Healthy code committed"
    return {
        "status": "ok",
        "commit": commit,
        "message": f"{what} to GitHub ({commit}). Render redeploys in about 2 to 4 minutes.",
    }


@app.post("/api/demo/break")
def demo_break():
    return _toggle(True)


@app.post("/api/demo/reset")
def demo_reset():
    return _toggle(False)


@app.get("/api/status")
def status():
    """Is checkout working in the code that is live right now, and how does GitHub compare?"""
    try:
        compute_total([{"product_id": 1, "quantity": 1}])
        healthy = True
    except Exception:
        healthy = False
    live = os.environ.get("RENDER_GIT_COMMIT", "")[:7] or "local"
    head = ctl.github_head()
    deploying = bool(head) and live != "local" and head["sha"] != live
    return {"healthy": healthy, "live_commit": live, "github": head, "deploying": deploying}


@app.get("/api/config")
def config():
    return {"dashboard_url": os.environ.get("DASHBOARD_URL", "")}


# ---- Log endpoint: the agent reads new log lines from here ----
@app.get("/_logs", include_in_schema=False)
def read_logs(request: Request, offset: int = 0):
    expected = os.environ.get("LOG_TOKEN")
    if not expected or request.headers.get("x-log-token") != expected:
        raise HTTPException(status_code=403, detail="Forbidden")
    path = os.environ.get("SHOP_LOG_PATH", DEFAULT_PATH)
    try:
        size = os.path.getsize(path)
    except OSError:
        return {"next": 0, "lines": []}
    if offset > size:
        offset = 0  # the log was wiped by a redeploy
    with open(path, "rb") as f:
        f.seek(offset)
        data = f.read()
    cut = data.rfind(b"\n") + 1  # whole lines only
    lines = [
        line for line in data[:cut].decode("utf-8", errors="replace").splitlines()
        if line.strip()
    ]
    return {"next": offset + cut, "lines": lines}


@app.get("/", include_in_schema=False)
@app.get("/store", include_in_schema=False)
def store():
    return FileResponse(BASE_DIR / "store.html")


if __name__ == "__main__":
    import uvicorn

    on_render = bool(os.environ.get("RENDER"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0" if on_render else "127.0.0.1",
        port=int(os.environ.get("PORT", "8010")),
        reload=not on_render,
    )