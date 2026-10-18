import os
import random
import sys
import time

import httpx

# Default is the live Render site. For a local server: $env:BASE_URL="http://127.0.0.1:8010"
BASE_URL = os.environ.get("BASE_URL", "https://shop-api-kwmr.onrender.com")


def hit(client, method, path, **kwargs):
    try:
        r = client.request(method, path, **kwargs)
        print(f"{method:4} {path:14} -> {r.status_code}")
    except httpx.HTTPError as e:
        print(f"{method:4} {path:14} -> connection error ({type(e).__name__})")


def main():
    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 1.5
    print(f"Sending traffic to {BASE_URL} every {delay}s. Ctrl+C to stop.")
    with httpx.Client(base_url=BASE_URL, timeout=15) as client:
        while True:
            hit(client, "GET", "/products")
            if random.random() < 0.2:
                hit(client, "GET", "/products/999")  # expected 404, never logged
            hit(client, "POST", "/cart",
                json={"product_id": random.choice([1, 2, 3]), "quantity": 1})
            hit(client, "POST", "/checkout")
            time.sleep(delay)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")