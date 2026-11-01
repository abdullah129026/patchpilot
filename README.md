# PatchPilot

AI Bug Reproduction Agent. Paste a public GitHub issue link, PatchPilot
reproduces the bug in a Docker sandbox and returns a reproduction script,
a failing test, and a suggested fix diff, with captured logs as proof.

## Status

Phase 1 (Foundation and Core Systems) is in progress under the Project
Phase Blueprint: phase-gated, no day slicing, and a completed phase never
advances without the founder's approval.

What exists now (foundation only):

- Agent service skeleton (FastAPI): health, fixture jobs, validated job
  submission into a filesystem job store.
- Deterministic verdict engine: verdicts are computed from exit codes
  and error-signature matches, never written by the LLM.
- Strict public GitHub issue URL validation, before any fetch or clone.
- CI running tests and lint on every push.
- Host rebuild script for the EC2 Docker host (provisioning itself is
  done in the AWS console, see `docs/deploy/ec2-setup.md`).
- Drafts of the Terms, Acceptable Use, and privacy pages in `docs/legal/`.

Deliberately not built yet: the experience design and page build slices
of Phase 1 wait for the D5 validation gate (5 maintainer conversations,
or an explicit waiver from the founder). The reproduction loop, Docker
runner, ceilings, and takedown path belong to Phases 2 and 3.

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
