import base64
import json
import os
import time
import urllib.error
import urllib.request

REPO = os.environ.get("GITHUB_REPO", "pranavvrao1-ai/shop-api")
BRANCH = os.environ.get("GITHUB_BRANCH", "main")

_cache = {"t": 0.0, "value": None}


def configured():
    return bool(os.environ.get("GITHUB_TOKEN"))


def _gh(method, path, payload=None):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set on this server")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/{path}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "shop-api-demo",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(body).get("message", body)
        except ValueError:
            pass
        raise RuntimeError(f"GitHub {err.code}: {str(body)[:200]}")


def set_broken(broken):
    """Commit the bug (or the healthy code) to GitHub.
    Returns the new short commit id, or None if main.py was already in that state."""
    f = _gh("GET", f"contents/main.py?ref={BRANCH}")
    text = base64.b64decode(f["content"]).decode("utf-8")
    old, new = ('"price":', '"cost":') if broken else ('"cost":', '"price":')
    if old not in text:
        return None
    res = _gh("PUT", "contents/main.py", {
        "message": "Rename price to cost in product catalog" if broken
                   else "Restore price key in product catalog",
        "content": base64.b64encode(text.replace(old, new).encode("utf-8")).decode("ascii"),
        "sha": f["sha"],
        "branch": BRANCH,
    })
    _cache["t"] = 0.0  # make the status bar refresh right away
    return res["commit"]["sha"][:7]


def github_head():
    """Latest commit on the branch as {'sha': '3f2a1bc', 'message': '...'}, or None. Cached 8 s."""
    now = time.time()
    if now - _cache["t"] < 8:
        return _cache["value"]
    value = None
    if configured():
        try:
            c = _gh("GET", f"commits/{BRANCH}")
            value = {"sha": c["sha"][:7], "message": c["commit"]["message"].splitlines()[0][:90]}
        except Exception:
            value = None
    _cache["t"] = now
    _cache["value"] = value
    return value