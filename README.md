# shop-api

A small demo online store, built as the test application for the **AI on-call engineer**
([incident-agent](https://github.com/Samuel777822/incident-agent)). When this app throws repeated errors,
the agent reads the logs, finds the root cause, writes and tests a fix, and opens a pull request here.

## How the demo works

1. **Break Checkout** commits a bug to this repository through the GitHub API (the catalog key `price` is
   renamed to `cost`). Render sees the commit and redeploys.
2. Once the broken code is live, checkout returns a 500 and each failure is written as one JSON line to `logs/app.log`.
   The **Auto traffic** button in the page keeps orders flowing so errors pile up.
3. The agent reads the log through the protected `/_logs` endpoint, diagnoses the bug and opens a pull request.
4. Merging the pull request redeploys the fixed code and checkout works again.

The status bar shows the live site's health and the latest commit on GitHub side by side.

## Endpoints

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/health` | Liveness check |
| GET | `/products`, `/products/{id}` | Catalog |
| GET / POST | `/cart` | View or add to the cart |
| POST | `/checkout` | Pay for the cart |
| GET | `/api/status` | Live health and GitHub commit comparison |
| POST | `/api/demo/break`, `/api/demo/reset` | Commit the bug / the healthy code to GitHub |
| GET | `/_logs?offset=N` | New log lines for the agent (needs the `X-Log-Token` header) |

## Environment variables (Render)

| Name | Purpose |
| --- | --- |
| `GITHUB_TOKEN` | Token with Contents read/write on this repo (Break/Reset and the status bar) |
| `LOG_TOKEN` | Shared secret the agent sends to read `/_logs` |
| `DASHBOARD_URL` | Optional: link to the agent's incident dashboard |

Render settings: build `pip install -r requirements.txt`, start `uvicorn main:app --host 0.0.0.0 --port $PORT`,
health check path `/health`, auto-deploy on commit.

## Run and test locally

```
pip install -r requirements.txt
python main.py        # http://127.0.0.1:8010
pytest -q
```

Note that pressing Break locally with `GITHUB_TOKEN` set also commits to the real repository.