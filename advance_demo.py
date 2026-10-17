import sqlite3
import sys

status = sys.argv[1] if len(sys.argv) > 1 else "pr_opened"
pr_url = "https://github.com/pranavvrao1-ai/shop-api/pull/2" if status == "pr_opened" else None

conn = sqlite3.connect("demo_incidents.db")
conn.execute("UPDATE incidents SET status=?, pr_url=? WHERE id=2", (status, pr_url))
conn.commit()
conn.close()
print("Incident 2 is now:", status)