import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "demo_incidents.db"
DB.unlink(missing_ok=True)

conn = sqlite3.connect(DB)
conn.executescript("""
CREATE TABLE IF NOT EXISTS incidents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  signature TEXT,
  status TEXT DEFAULT 'diagnosing',
  category TEXT,
  confidence TEXT,
  occurrences INTEGER DEFAULT 1,
  first_seen TEXT, last_seen TEXT,
  root_cause TEXT, explanation TEXT, report TEXT, pr_url TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  resolved_at TEXT
);
""")
conn.executemany(
    "INSERT INTO incidents (signature, status, category, confidence, occurrences, "
    "first_seen, last_seen, root_cause, explanation, report, pr_url) "
    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
    [
        ("KeyError@main.py:checkout", "failed", "code_bug", "low", 12,
         "2026-10-17T10:02:00+00:00", "2026-10-17T10:03:10+00:00",
         "Checkout reads a missing key", "Attempted fix did not pass tests",
         "long report text...", None),
        ("KeyError@main.py:checkout", "diagnosing", None, None, 5,
         "2026-10-17T10:15:00+00:00", "2026-10-17T10:15:05+00:00",
         None, None, None, None),
        ("KeyError@main.py:checkout", "pr_opened", "code_bug", "high", 9,
         "2026-10-17T10:20:00+00:00", "2026-10-17T10:20:09+00:00",
         "Product catalog key was renamed from price to cost",
         "Checkout still reads 'price'; restoring the key fixes it.",
         "long report text...",
         "https://github.com/pranavvrao1-ai/shop-api/pull/1"),
    ],
)
conn.commit()
conn.close()
print("Created", DB)