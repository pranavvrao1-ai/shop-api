import sqlite3

from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def test_incidents_empty_when_no_db(monkeypatch, tmp_path):
    monkeypatch.setenv("INCIDENTS_DB", str(tmp_path / "missing.db"))
    assert client.get("/api/incidents").json() == []


def test_incidents_reads_rows_without_report(monkeypatch, tmp_path):
    db = tmp_path / "incidents.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE incidents (id INTEGER PRIMARY KEY, status TEXT, report TEXT)")
    conn.execute("INSERT INTO incidents (status, report) VALUES ('diagnosing', 'long text')")
    conn.commit()
    conn.close()
    monkeypatch.setenv("INCIDENTS_DB", str(db))
    assert client.get("/api/incidents").json() == [{"id": 1, "status": "diagnosing", "report": "long text"}]

def test_dashboard_page():
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "Incidents" in r.text