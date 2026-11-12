"""LLM-down drill (Phase 5 failure drill), run locally or on the host.

Runs the real pipeline against a real public issue with the LLM
provider forced down, and proves the job ends in an honest failed
state (no verdict claimed, the reason in the job detail) instead of
a spinner or a fake verdict. The provider is forced down at the
exact seam the pipeline discovers it (build_llm_client), so the
drill stays true even on a host where a model id is configured.

Usage (from the repo root):
  python scripts/llm-down-drill.py

Exit 0: the job failed honestly. Exit 1: the job claimed a verdict
or hid the reason. Exit 2: the drill could not run (the issue fetch
failed, so the failure would not be about the LLM at all).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import pipeline  # noqa: E402
from app.job_store import create_job  # noqa: E402
from app.llm import ProviderUnavailable  # noqa: E402

DRILL_OWNER, DRILL_REPO, DRILL_NUMBER = "python-humanize", "humanize", 57


def run_drill(store_dir, job_id, *, build_llm=None):
    """Run one job with the provider down. Returns the finished job."""
    original = pipeline.build_llm_client
    try:
        if build_llm is not None:
            pipeline.build_llm_client = build_llm
        return pipeline.run_job(store_dir, job_id, issue=None, llm=None)
    finally:
        pipeline.build_llm_client = original


def main(argv=None) -> int:
    store = Path("data/drill-runs")
    store.mkdir(parents=True, exist_ok=True)
    job = create_job(store, DRILL_OWNER, DRILL_REPO, DRILL_NUMBER)

    def down():
        raise ProviderUnavailable("drill: LLM provider is down")

    try:
        finished = run_drill(store, job["id"], build_llm=down)
    except Exception as exc:  # noqa: BLE001 - the drill must report, not crash
        print(f"Drill error: {type(exc).__name__}")
        return 2
    print(f"Job: {job['id']}, status: {finished['status']}")
    print(f"Detail: {finished.get('detail')}")
    if finished.get("detail") in (
        "issue fetch failed",
        "GitHub rate-limited the issue fetch; try again later",
    ):
        print("Drill inconclusive: the issue fetch failed, so the LLM "
              "was never the question.")
        return 2
    if finished["status"] != "failed":
        print("FAIL: the job did not end failed with the LLM down.")
        return 1
    if finished.get("verdict") is not None:
        print("FAIL: a failed job still claims a verdict.")
        return 1
    if "LLM provider" not in (finished.get("detail") or ""):
        print("FAIL: the failure reason does not name the LLM provider.")
        return 1
    print("Honest failure: no verdict claimed, reason named.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
