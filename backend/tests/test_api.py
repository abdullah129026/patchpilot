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


def test_sample_fixtures_match_curated_fixture_file(tmp_path, monkeypatch):
    # Samples must stay real: every sample issue is one of the curated
    # fixtures, with the verdict the host suite recorded for it.
    import json
    from pathlib import Path

    curated = json.loads(
        (
            Path(__file__).resolve().parents[2] / "scripts" / "fixture_issues.json"
        ).read_text()
    )
    by_key = {(e["owner"], e["repo"], e["number"]): e for e in curated}
    recorded = {
        ("python-humanize", "humanize", 57): "REPRODUCED",
        ("PyCQA", "pyflakes", 764): "REPRODUCED",
        ("PyCQA", "pyflakes", 744): "NOT_REPRODUCED",
    }
    c = client(tmp_path, monkeypatch)
    listed = c.get("/api/jobs/fixtures").json()
    assert len(listed) == 3
    for sample in listed:
        key = (
            sample["issue"]["owner"],
            sample["issue"]["repo"],
            sample["issue"]["number"],
        )
        assert key in by_key, f"sample {sample['id']} is not a curated fixture"
        assert sample["verdict"] == recorded[key]
        assert sample["signature"] == by_key[key]["error_signature"]
        assert sample["fix_diff"] is None


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


def test_startup_sweep_marks_stale_running_jobs_failed(tmp_path, monkeypatch):
    from app.job_store import create_job, get_job, update_job

    monkeypatch.setenv("PATCHPILOT_JOB_DIR", str(tmp_path))
    job = create_job(tmp_path, "psf", "requests", 1)
    update_job(tmp_path, job["id"], status="running")
    with TestClient(create_app()):
        pass
    assert get_job(tmp_path, job["id"])["status"] == "failed"
