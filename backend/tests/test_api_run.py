from fastapi.testclient import TestClient

from app import main as main_module
from app.job_store import create_job, update_job


def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PATCHPILOT_JOB_DIR", str(tmp_path))
    return TestClient(main_module.create_app())


def test_run_missing_job_is_404(tmp_path, monkeypatch):
    assert (
        client(tmp_path, monkeypatch).post("/api/jobs/abcdef123456/run").status_code
        == 404
    )


def test_run_non_queued_job_is_409(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    job = create_job(tmp_path, "acme", "demo", 7)
    update_job(tmp_path, job["id"], status="done")
    assert c.post(f"/api/jobs/{job['id']}/run").status_code == 409


def test_run_starts_background_job_and_returns_202(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    job = create_job(tmp_path, "acme", "demo", 7)
    seen = {}

    def fake_run(store_dir, job_id, **kwargs):
        seen["job_id"] = job_id
        return update_job(store_dir, job_id, status="done", verdict="NOT_REPRODUCED")

    monkeypatch.setattr(main_module, "run_job", fake_run)
    resp = c.post(f"/api/jobs/{job['id']}/run")
    assert resp.status_code == 202
    assert seen["job_id"] == job["id"]
    # The background thread finishes the job; polling sees it done.
    for _ in range(50):
        done = c.get(f"/api/jobs/{job['id']}").json()
        if done["status"] == "done":
            break
    assert done["verdict"] == "NOT_REPRODUCED"


def test_stream_emits_done_job_and_missing_is_404(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    job = create_job(tmp_path, "acme", "demo", 7)
    update_job(tmp_path, job["id"], status="done", verdict="NOT_REPRODUCED")
    with c.stream("GET", f"/api/jobs/{job['id']}/stream") as resp:
        assert resp.status_code == 200
        assert "NOT_REPRODUCED" in resp.read().decode()
    assert c.get("/api/jobs/abcdef123456/stream").status_code == 404
