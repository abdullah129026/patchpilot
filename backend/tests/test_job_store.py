import pytest

from app.job_store import create_job, get_job


def test_round_trip(tmp_path):
    job = create_job(tmp_path, "psf", "requests", 1234)
    assert job["status"] == "queued"
    assert job["verdict"] is None
    again = get_job(tmp_path, job["id"])
    assert again["issue"]["number"] == 1234


def test_unknown_id_returns_none(tmp_path):
    assert get_job(tmp_path, "does-not-exist") is None


def test_path_traversal_id_returns_none(tmp_path):
    assert get_job(tmp_path, "../secret") is None
    with pytest.raises(ValueError):
        create_job(tmp_path, "a/b", "repo", 1)
