import pytest

from app.job_store import create_job, get_job, update_job


def test_round_trip(tmp_path):
    job = create_job(tmp_path, "psf", "requests", 1234)
    assert job["status"] == "queued"
    assert job["verdict"] is None
    again = get_job(tmp_path, job["id"])
    assert again["issue"]["number"] == 1234


def test_concurrent_read_never_sees_a_torn_report(tmp_path):
    """A reader polling while updates land must never see a missing job.

    update_job used to truncate report.json and then write it, so a
    concurrent read could catch a partial file and the API answered
    404 for a job that exists. This failed CI once in
    test_run_starts_background_job_and_returns_202.
    """
    import threading

    job = create_job(tmp_path, "psf", "requests", 1234)
    stop = False
    misses = []

    def writer():
        n = 0
        while not stop:
            update_job(tmp_path, job["id"], attempts=[{"n": n, "log": "x" * 5000}])
            n += 1

    def reader():
        while not stop:
            if get_job(tmp_path, job["id"]) is None:
                misses.append(True)

    wt = threading.Thread(target=writer)
    rt = threading.Thread(target=reader)
    wt.start()
    rt.start()
    import time

    time.sleep(1)
    stop = True
    wt.join()
    rt.join()
    assert misses == []


def test_create_job_with_ref_stores_it(tmp_path):
    job = create_job(tmp_path, "psf", "requests", 1234, ref="a" * 40)
    assert get_job(tmp_path, job["id"])["issue"]["ref"] == "a" * 40


def test_create_job_rejects_bad_ref(tmp_path):
    with pytest.raises(ValueError):
        create_job(tmp_path, "psf", "requests", 1234, ref="main")


def test_unknown_id_returns_none(tmp_path):
    assert get_job(tmp_path, "does-not-exist") is None


def test_path_traversal_id_returns_none(tmp_path):
    assert get_job(tmp_path, "../secret") is None
    with pytest.raises(ValueError):
        create_job(tmp_path, "a/b", "repo", 1)
