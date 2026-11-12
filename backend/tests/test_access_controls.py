"""Phase 2 access and abuse controls: ceilings, queue, takedown.

Tests first, per the TDD skill: each test names the behaviour that
would make it fail, and the limits module does not exist yet when
these are written.
"""

from fastapi.testclient import TestClient

from app.main import create_app


def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PATCHPILOT_JOB_DIR", str(tmp_path))
    return TestClient(create_app())


def submit(c, ip, url="https://github.com/a/b/issues/9"):
    return c.post("/api/jobs", json={"issue_url": url}, headers={"X-Forwarded-For": ip})


def test_global_daily_ceiling_stops_fourth_job(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    for i in range(3):
        resp = submit(c, f"203.0.113.{i + 1}")
        assert resp.status_code == 201, resp.text
    fourth = submit(c, "203.0.113.99")
    assert fourth.status_code == 429
    assert "daily" in fourth.json()["detail"].lower()


def test_per_ip_daily_ceiling_stops_third_job_from_same_ip(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    assert submit(c, "203.0.113.7").status_code == 201
    assert submit(c, "203.0.113.7").status_code == 201
    third = submit(c, "203.0.113.7")
    assert third.status_code == 429
    assert "per-address" in third.json()["detail"].lower()
    # A different address is unaffected by the per-IP ceiling.
    assert submit(c, "203.0.113.8").status_code == 201


def test_rejected_url_does_not_burn_quota(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    bad = c.post(
        "/api/jobs",
        json={"issue_url": "https://example.com/x"},
        headers={"X-Forwarded-For": "203.0.113.7"},
    )
    assert bad.status_code == 422
    assert submit(c, "203.0.113.7").status_code == 201
    assert submit(c, "203.0.113.7").status_code == 201


def test_limits_endpoint_reports_usage(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    submit(c, "203.0.113.7")
    resp = c.get("/api/limits", headers={"X-Forwarded-For": "203.0.113.7"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["daily_used"] == 1
    assert body["daily_ceiling"] == 3
    assert body["per_ip_used"] == 1
    assert body["per_ip_ceiling"] == 2


def test_queue_position_counts_active_jobs(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    first = submit(c, "203.0.113.1")
    assert first.json()["queue_position"] == 1
    second = submit(c, "203.0.113.2")
    assert second.json()["queue_position"] == 2
    assert second.json()["status"] == "queued"


def test_delete_token_removes_job_end_to_end(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    created = submit(c, "203.0.113.7")
    assert created.status_code == 201
    job_id = created.json()["id"]
    token = created.json()["delete_token"]
    assert token

    # The token and its hash never leak through the read endpoint.
    fetched = c.get(f"/api/jobs/{job_id}")
    assert "delete_token" not in fetched.json()
    assert "delete_token_hash" not in fetched.json()

    assert c.delete(f"/api/jobs/{job_id}").status_code == 403
    assert (
        c.delete(f"/api/jobs/{job_id}", headers={"X-Delete-Token": "wrong"}).status_code
        == 403
    )
    gone = c.delete(f"/api/jobs/{job_id}", headers={"X-Delete-Token": token})
    assert gone.status_code == 204
    assert c.get(f"/api/jobs/{job_id}").status_code == 404
    assert (
        c.delete(f"/api/jobs/{job_id}", headers={"X-Delete-Token": token}).status_code
        == 404
    )


def test_browser_frontend_can_call_api_cross_origin(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    resp = c.options(
        "/api/jobs",
        headers={
            "Origin": "https://patchpilot.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == "*"


def test_takedown_request_for_unknown_and_known_report(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    assert (
        c.post(
            "/api/jobs/nope12345678/takedown-request",
            json={"contact": "owner@example.com", "reason": "please remove"},
        ).status_code
        == 404
    )
    created = submit(c, "203.0.113.7")
    job_id = created.json()["id"]
    resp = c.post(
        f"/api/jobs/{job_id}/takedown-request",
        json={
            "contact": "owner@example.com",
            "reason": "this is my repo, please remove",
        },
    )
    assert resp.status_code == 202
    # The report itself is untouched by a mere request: removal is the
    # founder's step, or the submitter's delete token.
    assert c.get(f"/api/jobs/{job_id}").status_code == 200


def test_spoofed_forwarded_for_cannot_rotate_per_ip_ceiling(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    assert submit(c, "203.0.113.7").status_code == 201
    assert submit(c, "203.0.113.7").status_code == 201
    # A client can prepend any address it likes to X-Forwarded-For;
    # the proxy appends the address it actually saw last, so that is
    # the one the ceiling must count.
    spoofed = c.post(
        "/api/jobs",
        json={"issue_url": "https://github.com/a/b/issues/9"},
        headers={"X-Forwarded-For": "203.0.113.99, 203.0.113.7"},
    )
    assert spoofed.status_code == 429
    assert "per-address" in spoofed.json()["detail"].lower()


def test_concurrent_submissions_cannot_overshoot_global_ceiling(tmp_path, monkeypatch):
    import threading

    from app import limits

    barrier = threading.Barrier(6)
    results = []

    def attempt(n):
        barrier.wait()
        try:
            limits.check_and_record(tmp_path, f"203.0.113.{n}")
            results.append("ok")
        except limits.LimitExceeded:
            results.append("rejected")

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # Six parallel submissions from six addresses, global ceiling 3:
    # exactly three get in, the rest are refused.
    assert sorted(results) == ["ok", "ok", "ok", "rejected", "rejected", "rejected"]
    assert limits.global_today(tmp_path) == 3
