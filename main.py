from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
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
    1: {"name": "Wireless Mouse", "price": 799},
    2: {"name": "Mechanical Keyboard", "price": 3499},
    3: {"name": "USB-C Hub", "price": 1899},
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