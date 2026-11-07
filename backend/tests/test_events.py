"""Tests for the first-party analytics events (Phase 4, Phase 0 0.5)."""

from fastapi.testclient import TestClient

from app.events import EVENTS, event_counts, record_event, verdict_distribution
from app.main import create_app


def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PATCHPILOT_JOB_DIR", str(tmp_path))
    return TestClient(create_app())


def test_record_event_rejects_unknown_names(tmp_path):
    try:
        record_event(tmp_path, "not_a_real_event")
    except ValueError:
        return
    raise AssertionError("unknown event name was accepted")


def test_record_event_rejects_unknown_verdict(tmp_path):
    try:
        record_event(tmp_path, "verdict_shown", verdict="MADE_UP")
    except ValueError:
        return
    raise AssertionError("unknown verdict was accepted")


def test_record_event_appends_jsonl_and_counts(tmp_path):
    record_event(tmp_path, "landing_view")
    record_event(tmp_path, "landing_view")
    record_event(tmp_path, "verdict_shown", verdict="REPRODUCED")
    counts = event_counts(tmp_path)
    assert counts["landing_view"] == 2
    assert counts["verdict_shown"] == 1
    lines = (tmp_path / "events.jsonl").read_text().splitlines()
    assert len(lines) == 3
    assert "127.0.0.1" not in (tmp_path / "events.jsonl").read_text()
    assert "github.com" not in (tmp_path / "events.jsonl").read_text()


def test_all_eight_phase0_events_are_known():
    assert EVENTS == {
        "landing_view",
        "job_submitted",
        "job_started",
        "verdict_shown",
        "report_copied_script",
        "report_copied_test",
        "diff_expanded",
        "sample_report_opened",
    }


def test_events_endpoint_accepts_and_rejects(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    ok = c.post("/api/events", json={"event": "landing_view"})
    assert ok.status_code == 202
    assert ok.json()["status"] == "recorded"
    bad = c.post("/api/events", json={"event": "not_a_real_event"})
    assert bad.status_code == 422
    bad_verdict = c.post(
        "/api/events", json={"event": "verdict_shown", "verdict": "MADE_UP"}
    )
    assert bad_verdict.status_code == 422


def test_stats_endpoint_counts_events_verdicts_and_jobs_today(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    c.post("/api/events", json={"event": "landing_view"})
    c.post("/api/events", json={"event": "sample_report_opened"})
    created = c.post("/api/jobs", json={"issue_url": "https://github.com/a/b/issues/9"})
    assert created.status_code == 201
    stats = c.get("/api/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert body["events"]["landing_view"] == 1
    assert body["events"]["sample_report_opened"] == 1
    assert body["jobs_today"] == 1
    assert body["verdicts"] == {}
    # A finished job with a verdict shows up in the distribution.
    from app.job_store import update_job

    update_job(tmp_path, created.json()["id"], status="done", verdict="REPRODUCED")
    assert c.get("/api/stats").json()["verdicts"] == {"REPRODUCED": 1}
    assert verdict_distribution(tmp_path) == {"REPRODUCED": 1}
