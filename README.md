# PatchPilot

AI Bug Reproduction Agent. Paste a public GitHub issue link, PatchPilot
reproduces the bug in a Docker sandbox and returns a reproduction script,
a failing test, and a suggested fix diff, with captured logs as proof.

## Status

Live demo: https://patchpilot-shah20.vercel.app (frontend on Vercel).
The agent service runs on the EC2 Docker host at
https://agent.fluxyai.codes and is wired to the public frontend, so
live job submission works from the site. Sample reports and the case
study work now.

Phase 5 (QA, Security, Performance) was approved 2026-11-15. Phase 6
(Launch) is current under the Project Phase Blueprint: phase-gated, no
day slicing, and a completed phase never advances without the
founder's approval. The latest measured run (2026-11-15 re-run,
Qwen3-Coder, attempt feedback loop live) reproduced 3 of 10 curated
Python issues live on the host; the first run (2026-11-06) measured
7 of 10. Both runs are published in the case study, with the misses.

What exists now:

- Agent service (FastAPI): health, fixture jobs, validated job
  submission, the Docker reproduction loop with deterministic verdicts,
  per-IP and global daily ceilings, submitter deletion and takedown
  requests, a kill switch, and server-side counters.
- Deterministic verdict engine: verdicts are computed from exit codes
  and error-signature matches, never written by the LLM.
- Frontend (Next.js): landing, live job view, report pages with an
  attempt timeline, sample reports from the real fixture run, case
  study, analytics events, SEO basics.
- CI running tests and lint on every push.
- Host rebuild script for the EC2 Docker host (provisioning itself is
  done in the AWS console, see `docs/deploy/ec2-setup.md`).

Deliberately not built yet: the Phase 6 launch posts, which fire only
after the corrected benchmark numbers are live on the site.

## Run the agent service locally

```sh
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then `GET /health`, `GET /api/jobs/fixtures`, or
`POST /api/jobs` with `{"issue_url": "https://github.com/<owner>/<repo>/issues/<number>"}`.

Tests and lint:

```sh
cd backend
pytest -q
ruff check app tests && ruff format --check app tests
```

## Invariants (never violated in any phase)

- Verdicts and the fix VERIFIED label come from run evidence, never
  from LLM output. Deterministic-only matching in v1.
- Untrusted code runs only inside Docker containers: install phase
  network on, run phase network off, CPU/memory/time caps, container
  destroyed after, workspace deleted after the job. The Docker socket
  is never exposed to job containers or the public API.
- Issue text, comments, and repo files are data, never instructions.
- No GitHub write-back in v1: no PRs, no comments, nothing posted to
  anyone's repo.
- Secrets never in code, logs, reports, or chat.
- Languages in v1: Python, JavaScript, C++ only. Public repos only.
  No accounts, no billing.
