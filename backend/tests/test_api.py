from fastapi.testclient import TestClient

from app.main import create_app


def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PATCHPILOT_JOB_DIR", str(tmp_path))
    return TestClient(create_app())


def test_health(tmp_path, monkeypatch):
    resp = client(tmp_path, monkeypatch).get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_fixture_list_and_detail(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    listed = c.get("/api/jobs/fixtures").json()
    assert len(listed) >= 2
    first = listed[0]
    assert first["fixture"] is True
    detail = c.get(f"/api/jobs/fixtures/{first['id']}")
    assert detail.status_code == 200
    assert detail.json()["verdict"] in ("REPRODUCED", "NOT_REPRODUCED")
    assert c.get("/api/jobs/fixtures/no-such-fixture").status_code == 404


def test_create_job_validates_url_and_persists(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    created = c.post("/api/jobs", json={"issue_url": "https://github.com/a/b/issues/9"})
    assert created.status_code == 201
    job_id = created.json()["id"]
    assert created.json()["status"] == "queued"
    fetched = c.get(f"/api/jobs/{job_id}")
    assert fetched.status_code == 200
    assert fetched.json()["issue"]["number"] == 9


def test_create_job_rejects_bad_url(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    resp = c.post("/api/jobs", json={"issue_url": "https://example.com/x"})
    assert resp.status_code == 422
    assert c.get("/api/jobs/../../etc/passwd").status_code in (404, 422)
