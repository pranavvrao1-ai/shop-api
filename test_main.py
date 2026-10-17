import json
import os

import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def clean_cart():
    main.CART.clear()
    yield
    main.CART.clear()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_products():
    r = client.get("/products")
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_get_product():
    r = client.get("/products/1")
    assert r.status_code == 200
    assert r.json()["name"] == "Wireless Mouse"
    assert client.get("/products/999").status_code == 404


def test_cart():
    r = client.post("/cart", json={"product_id": 1, "quantity": 2})
    assert r.status_code == 200
    r = client.get("/cart")
    assert r.json()["items"] == [{"product_id": 1, "quantity": 2}]


def test_checkout():
    client.post("/cart", json={"product_id": 1, "quantity": 2})
    r = client.post("/checkout")
    assert r.status_code == 200
    assert r.json()["total"] == 1598  # 799 * 2


def test_unhandled_error_is_logged_as_json(monkeypatch):
    # Simulate the bug: product with no "price" key
    monkeypatch.setitem(main.PRODUCTS, 1, {"name": "Broken"})
    client.post("/cart", json={"product_id": 1, "quantity": 1})
    r = client.post("/checkout")
    assert r.status_code == 500

    with open(os.environ["SHOP_LOG_PATH"], encoding="utf-8") as f:
        record = json.loads(f.readlines()[-1])
    assert set(record) == {"ts", "level", "service", "message", "traceback"}
    assert record["service"] == "shop-api"
    assert "KeyError" in record["traceback"]

    def test_dashboard_page():
        r = client.get("/dashboard")
        assert r.status_code == 200
        assert "Incidents" in r.text