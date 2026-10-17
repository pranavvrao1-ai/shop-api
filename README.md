# shop-api

A small demo online store built as the test application for an **AI on-call engineer**.
When this app throws repeated errors in production, the companion project
[incident-agent](https://github.com/Samuel777822/incident-agent) reads the logs, finds the root cause,
asks an LLM for a fix, tests it, and opens a pull request here. A human clicks Merge.

This repo contains:

- the store itself (FastAPI, in-memory data)
- structured JSON error logging that the agent reads
- scripts that generate traffic and deliberately break (and repair) the app, so the demo can be repeated
- a live dashboard that shows the agent's incidents

## Endpoints

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/products` | List all products |
| GET | `/products/{id}` | One product (404 if unknown) |
| GET | `/cart` | View the cart |
| POST | `/cart` | Add `{"product_id": 1, "quantity": 2}` to the cart |
| POST | `/checkout` | Pay for the cart; reads `PRODUCTS[id]["price"]` |
| GET | `/dashboard` | Incident dashboard (HTML, refreshes every 3 seconds) |
| GET | `/api/incidents` | Incidents from the agent's database, newest first (JSON) |

Interactive API docs are at `/docs` while the server runs.

## Setup

Requires Python 3.10 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

On macOS or Linux, use `.venv/bin/python` instead of `.\.venv\Scripts\python.exe`.

Run the tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Error log format

Every unexpected error (HTTP 500) writes exactly one JSON line to `logs/app.log`:

```json
{"ts": "2026-10-17T12:56:14.817405+00:00", "level": "ERROR", "service": "shop-api",
 "message": "POST /checkout failed: KeyError: 'price'", "traceback": "Traceback (most recent call last):\n  ..."}
```

- `ts` is UTC in ISO 8601 format.
- `traceback` is the full traceback as one string; newlines are escaped, so one error is always one line.
- Expected errors (404 for a missing product, 400 for an empty cart) are not logged, so only real bugs reach the agent.
- Set `SHOP_LOG_PATH` to write the log somewhere else (the tests do this).

## The demo scripts

| Script | Purpose |
|---|---|
| `traffic.py` | Loops over the endpoints like a customer (browse, add to cart, check out) so errors pile up when something breaks. Optional argument: delay in seconds. |
| `break.py` | Renames the `"price"` keys in the product catalog to `"cost"`, commits, and pushes. `/checkout` then raises `KeyError: 'price'`. Use `--no-push` for a local-only practice run. |
| `reset.py` | Restores the working code, commits, and pushes. Also accepts `--no-push`. |

The agent reads the code from GitHub, so a real demo run must push the bug (no `--no-push`).
After every run, `reset.py` leaves `main` healthy again.

## Dashboard

Open `http://127.0.0.1:8000/dashboard`. It shows each incident's status
(`diagnosing`, `diagnosed`, `pr_opened`, `failed`), the error signature, how many times it occurred,
the root cause and recommended fix, and a link to the pull request.

The dashboard reads the agent's SQLite database **read-only**. By default it looks for
`../incident-agent/incidents.db`. Point it elsewhere with:

```powershell
$env:INCIDENTS_DB = "C:\path\to\incidents.db"
```

`seed_incidents.py` and `advance_demo.py` create and update a practice database
(`demo_incidents.db`) so the dashboard can be tried without the agent.

## Running the full demo

1. Clean start: stop the server, traffic and tailer; delete `logs/` and the agent's `incidents.db`; run `reset.py`.
2. Start the server, then `traffic.py` (every line should be `200`, except the occasional deliberate 404).
3. From the `incident-agent` folder, start its tailer on `shop-api/logs/app.log`.
4. Run `break.py`. Checkout starts returning 500, and an incident appears on the dashboard.
5. The agent diagnoses the bug, verifies a fix, and opens a pull request.
6. A human clicks **Merge**. Run `reset.py` (or `git pull`) so the running app gets the fix.

## Project layout

```
main.py               FastAPI app, logging middleware, dashboard endpoints
jsonlog.py            JSON log formatter and logger setup
dashboard.html        the incident dashboard page
traffic.py            traffic generator
break.py / reset.py   introduce and repair the demo bug
seed_incidents.py     practice database for the dashboard
advance_demo.py       change a practice incident's status
test_main.py          tests for the five store endpoints and the log format
test_dashboard.py     tests for the incident API and dashboard page
conftest.py           keeps test errors out of the real log
```
