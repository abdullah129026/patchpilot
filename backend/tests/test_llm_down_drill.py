"""Tests for the LLM-down drill: the drill itself must be honest
about what it proves, using fakes so no network or provider is
needed here. The live run happens via scripts/llm-down-drill.py.
"""

import importlib.util
from pathlib import Path

from app import pipeline
from app.job_store import create_job
from app.llm import ProviderUnavailable

_DRILL = Path(__file__).resolve().parents[2] / "scripts" / "llm-down-drill.py"
_spec = importlib.util.spec_from_file_location("llm_down_drill", _DRILL)
_drill = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_drill)
run_drill = _drill.run_drill

ISSUE = {"title": "Crash", "body": "Traceback:\nValueError: bad key\n"}


def _down():
    raise ProviderUnavailable("drill: LLM provider is down")


def test_drill_fails_honestly_when_provider_is_down(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "fetch_issue_cached", lambda *a, **k: ISSUE)
    job = create_job(tmp_path, "python-humanize", "humanize", 57)
    finished = run_drill(tmp_path, job["id"], build_llm=_down)
    assert finished["status"] == "failed"
    assert finished["verdict"] is None
    assert "LLM provider" in (finished.get("detail") or "")


def test_drill_builder_is_restored_afterwards(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "fetch_issue_cached", lambda *a, **k: ISSUE)
    before = pipeline.build_llm_client
    job = create_job(tmp_path, "python-humanize", "humanize", 57)
    run_drill(tmp_path, job["id"], build_llm=_down)
    assert pipeline.build_llm_client is before
