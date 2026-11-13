"""Takedown drill (Phase 5): prove the report-removal paths work
end to end against a live agent service.

Starts from a running local backend (the host run uses the same
script against the deployed service, with the store path on that
host). Exercises: delete without a token (403), delete with a wrong
token (403), delete with the submitter token (204, then 404), and a
takedown request (202, report untouched, request recorded in the
store's .takedown-requests.jsonl).

Usage (from the repo root, with a local backend running):
  PATCHPILOT_JOB_DIR=/tmp/pp5-takedown-jobs python -m uvicorn \
      app.main:app --host 127.0.0.1 --port 8101
  python scripts/takedown-drill.py \
      --agent http://127.0.0.1:8101 --store /tmp/pp5-takedown-jobs

Exit 0: every check passed. Exit 1: a check failed. Exit 2: the
agent service could not be reached.
"""

import argparse
import json
import sys
from pathlib import Path

import httpx

ISSUE_URL = "https://github.com/python-humanize/humanize/issues/57"


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" ({detail})" if detail else ""))
    return ok


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default="http://127.0.0.1:8101")
    parser.add_argument("--store", default="data/jobs")
    args = parser.parse_args(argv)
    passed = True
    try:
        # trust_env=False: the drill only ever talks to localhost, and
        # httpx otherwise parses NO_PROXY at Client construction, which
        # breaks on bracketed IPv6 entries (e.g. [fd8b:...]) in some
        # sandbox environments. Localhost never needs a proxy.
        with httpx.Client(
            base_url=args.agent, timeout=30, trust_env=False
        ) as client:
            created = client.post("/api/jobs", json={"issue_url": ISSUE_URL})
            if created.status_code != 201:
                print(f"Agent did not accept the drill job: {created.status_code}")
                return 2
            job = created.json()
            job_id, token = job["id"], job["delete_token"]
            print(f"Drill job: {job_id}")
            passed &= check(
                "delete without a token is refused",
                client.delete(f"/api/jobs/{job_id}").status_code == 403,
            )
            passed &= check(
                "delete with a wrong token is refused",
                client.delete(
                    f"/api/jobs/{job_id}", headers={"X-Delete-Token": "wrong"}
                ).status_code
                == 403,
            )
            passed &= check(
                "delete with the submitter token removes the job",
                client.delete(
                    f"/api/jobs/{job_id}", headers={"X-Delete-Token": token}
                ).status_code
                == 204,
            )
            passed &= check(
                "deleted job reads 404",
                client.get(f"/api/jobs/{job_id}").status_code == 404,
            )
            second = client.post("/api/jobs", json={"issue_url": ISSUE_URL})
            if second.status_code != 201:
                print("Agent did not accept the second drill job; "
                      "the daily ceiling may be spent.")
                return 2
            job2 = second.json()["id"]
            resp = client.post(
                f"/api/jobs/{job2}/takedown-request",
                json={
                    "contact": "drill@example.com",
                    "reason": "Phase 5 takedown drill",
                },
            )
            passed &= check("takedown request is accepted", resp.status_code == 202)
            passed &= check(
                "report stays up after a mere request",
                client.get(f"/api/jobs/{job2}").status_code == 200,
            )
            passed &= check(
                "takedown request for an unknown job is 404",
                client.post(
                    "/api/jobs/nope12345678/takedown-request",
                    json={"contact": "", "reason": "x"},
                ).status_code
                == 404,
            )
    except httpx.HTTPError as exc:
        print(f"Agent service could not be reached: {type(exc).__name__}")
        return 2
    record_file = Path(args.store) / ".takedown-requests.jsonl"
    try:
        recorded = [
            json.loads(line)
            for line in record_file.read_text().splitlines()
            if line.strip()
        ]
    except OSError:
        recorded = []
    passed &= check(
        "takedown request is recorded in the store",
        any(
            r.get("job_id") == job2 and r.get("reason") == "Phase 5 takedown drill"
            for r in recorded
        ),
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
