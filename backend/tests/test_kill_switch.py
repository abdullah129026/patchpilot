"""Kill switch (Phase 4 launch checklist, Phase 0 risk 2).

The founder pauses the public demo by placing a `.paused` file in the
job store (host step, docs/deploy/kill-switch.md). While it is there,
no new job is accepted and no queued job starts; the limits and stats
endpoints say so honestly. There is deliberately no API endpoint to
pause: v1 has no accounts, so a public pause switch would be an abuse
vector of its own.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PATCHPILOT_JOB_DIR", str(tmp_path))
    return TestClient(create_app())


def pause(tmp_path):
    (Path(tmp_path) / ".paused").write_text("paused by the founder\n")


def submit(c, ip, url="https://github.com/a/b/issues/9"):
    return c.post("/api/jobs", json={"issue_url": url}, headers={"X-Forwarded-For": ip})


def test_paused_service_refuses_new_jobs_with_503(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    pause(tmp_path)
    resp = submit(c, "203.0.113.7")
    assert resp.status_code == 503
    assert "paused" in resp.json()["detail"].lower()


def test_paused_service_does_not_burn_quota(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    pause(tmp_path)
    assert submit(c, "203.0.113.7").status_code == 503
    (Path(tmp_path) / ".paused").unlink()
    assert submit(c, "203.0.113.7").status_code == 201
    assert submit(c, "203.0.113.7").status_code == 201


def test_paused_service_refuses_to_start_queued_jobs(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    created = submit(c, "203.0.113.7")
    assert created.status_code == 201
    job_id = created.json()["id"]
    pause(tmp_path)
    resp = c.post(f"/api/jobs/{job_id}/run")
    assert resp.status_code == 503
    assert "paused" in resp.json()["detail"].lower()


def test_limits_endpoint_reports_paused(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    assert c.get("/api/limits").json()["paused"] is False
    pause(tmp_path)
    assert c.get("/api/limits").json()["paused"] is True


def test_paused_rejection_is_counted_in_stats(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    pause(tmp_path)
    assert submit(c, "203.0.113.7").status_code == 503
    assert submit(c, "203.0.113.8").status_code == 503
    stops = c.get("/api/stats").json()["ceiling_stops_today"]
    assert stops.get("paused") == 2
