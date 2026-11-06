"""Fixture suite runner (Phase 3 DONE criterion).

Reads a JSON list of curated issues, runs each through the real
pipeline, and prints the verdict distribution. An entry is only
recorded after its issue has been fetched from the GitHub API and
its merged fix confirmed; see docs/fixture-suite.md. Each entry
carries base_commit, the first parent of the fix merge: the job
runs the repo at that commit, so the bug is present to reproduce.
Exit code 0 requires at least 3 REPRODUCED out of 10, the Phase 0
target.

The model under test comes from the environment
(PATCHPILOT_BEDROCK_MODEL_ID); run the suite once per candidate
model and compare the distributions to arbitrate D8.

Usage: python scripts/run-fixture-suite.py fixture_issues.json
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.job_store import create_job  # noqa: E402
from app.pipeline import run_job  # noqa: E402


def load_entries(path: str | Path) -> list:
    entries = json.loads(Path(path).read_text())
    for entry in entries:
        missing = {"owner", "repo", "number", "base_commit"} - set(entry)
        if missing:
            raise ValueError(f"fixture entry {entry} is missing {sorted(missing)}")
    return entries


def main() -> int:
    entries = load_entries(sys.argv[1])
    store = Path("data/fixture-runs")
    store.mkdir(parents=True, exist_ok=True)
    model = os.environ.get("PATCHPILOT_BEDROCK_MODEL_ID", "") or "(no model set)"
    print(f"Model: {model}")
    verdicts: dict[str, int] = {}
    for entry in entries:
        job = create_job(
            store,
            entry["owner"],
            entry["repo"],
            entry["number"],
            ref=entry["base_commit"],
        )
        result = run_job(store, job["id"])
        verdict = (result or {}).get("verdict") or "ERROR"
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
        print(f"{entry['owner']}/{entry['repo']}#{entry['number']}: {verdict}")
    print(f"\nTotal: {len(entries)}, reproduced: {verdicts.get('REPRODUCED', 0)}")
    print(f"Distribution: {verdicts}")
    if len(entries) != 10:
        print("Suite is incomplete: 10 curated issues are required.")
        return 2
    return 0 if verdicts.get("REPRODUCED", 0) >= 3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
