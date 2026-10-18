import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from demo_tools.ctl import set_broken
from jsonlog import DEFAULT_PATH, get_logger

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


@app.get("/api/status", include_in_schema=False)
def status():
    """Lets the storefront show whether the code that is live right now is healthy."""
    healthy = all("price" in p for p in PRODUCTS.values())
    commit = os.environ.get("RENDER_GIT_COMMIT", "local")[:7]
    return {"healthy": healthy, "commit": commit}


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
        price = prod["price"]
        total += price * item["quantity"]

    CART.clear()
    return {"status": "paid", "total": total}


# ---- Demo controls: break / reset the catalog ----
def _launch(script_name):
    """Local only: run break.py or reset.py in a separate process."""
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


def _demo_toggle(broken, script):
    if not os.environ.get("RENDER"):  # running on your laptop: use the git scripts
        _launch(script)
        return {"status": "ok", "message": f"Running {script} locally. Checkout changes in a few seconds."}
    try:  # running on Render: commit through the GitHub API, Render then redeploys
        changed = set_broken(broken)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"GitHub commit failed: {type(exc).__name__}: {exc}"
        )
    if not changed:
        return {"status": "noop", "message": "The code is already in that state."}
    return {"status": "ok", "message": "Committed to GitHub. Render is redeploying (2 to 4 minutes)."}


@app.post("/api/demo/break")
def demo_break():
    return _demo_toggle(True, "break.py")


@app.post("/api/demo/reset")
def demo_reset():
    return _demo_toggle(False, "reset.py")


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
        # mode=ro: this app can only READ the agent's database, never change it
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
    uvicorn.run("main:app", host="127.0.0.1", port=8010, reload=True)