# Phase 5 security audit (living record)

Phase 5 DONE needs: the security checklist from the standing build
rules passes, no critical or high findings remain open, and the
failure drills (host down, LLM down, GitHub rate-limited) all end in
honest user-facing states. This file records the audit evidence as
the phase runs; the gate document at completion summarises it for
the founder.

## Dependency audit — 2026-11-12

Tool: pip-audit against backend/requirements.txt, fresh venv.

Before (fastapi 0.115.6 / starlette 0.41.3 / pytest 8.3.4): 16 known
vulnerabilities in 2 packages. starlette 0.41.3 carried PYSEC-2026-1941,
PYSEC-2026-1942, PYSEC-2026-161, PYSEC-2026-2281, PYSEC-2026-2280,
PYSEC-2026-249 and PYSEC-2026-248 (fix versions up to starlette 1.3.1);
pytest 8.3.4 carried PYSEC-2026-1845 (fix 9.0.3).

Fix: fastapi 0.140.0 (first release whose starlette range has no upper
bound, so starlette 1.x is allowed), starlette pinned explicitly at
1.3.1, pytest 9.0.3. Verified: full suite 117/117, ruff clean,
pip-audit clean after the upgrade.

## Findings

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | Per-job token budget defined (TOKEN_BUDGET_PER_JOB, 120_000) but never enforced; the attempt loop only checks wall time | High | Fixed: loop stops with LIMIT REACHED, a reproducing attempt keeps its verdict, no test/diff spend once over budget (121 tests) |
| 2 | GitHub issue fetch does not distinguish rate limiting (403/429) from other failures; the job reports a generic "issue fetch failed" | Medium | Fixed: RateLimitedError on 429 or exhausted quota, pipeline reports SETUP_FAILED with "try again later" (125 tests) |
| 3 | Per-IP ceiling reads the first X-Forwarded-For entry, which a client can spoof; Caddy appends the real client IP last | Medium | Fixed: last entry wins, single-proxy assumption documented (130 tests) |
| 4 | Submission ceiling check-then-record is not atomic; parallel submissions can overshoot the global daily ceiling | Medium | Fixed: check_and_record under one lock, threaded test proves exactly 3 of 6 parallel submissions get in (130 tests) |
| 5 | Full issue body is pasted into every LLM prompt with no cap; a pathological body blows the context window on the first call | Medium | Fixed: prompt excerpt capped at 6000 chars, analyzer still reads the full body (128 tests) |
| 6 | A job whose LLM provider is missing still clones and installs the repo before failing | Low | Fixed: fail-fast check moved before clone (121 tests) |
| 7 | A failed job's reason (job detail) is never shown on the job or report page; the user sees "failed" with no explanation | Medium | Fixed: detail rendered as text on both pages, verified by Playwright screenshots of a real failed job (134 tests) |
| 8 | A job start that fails on the job page leaves the job visibly "queued" forever with no retry and no error | Medium | Fixed: start error shown with a retry button, verified against a stub agent returning 503 (134 tests) |
| 9 | A job left "running" by a dead service process stays "running" forever; nothing marks it failed | Medium | Fixed: startup sweep marks stale running jobs failed with an honest detail (132 tests) |
| 10 | Base images pinned by tag only (python:3.12-slim, node:22-slim, gcc:13); a tag can move under the build | Medium | Fixed 2026-11-12: digests fetched on the EC2 host (docker pull + RepoDigests; buildx is not installed there) and pinned as image@sha256:... in backend/app/config.py. python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b, node:22-slim@sha256:e9f565d32859f0cbfb52125eafe8be39390f24dac302dc3cdf566e8ba3ab21ee, gcc:13@sha256:8c0fe724784c6d617cb582f79ddaf5dd2233aaba2fb7a14e0b9d03348fea8088. Takes effect on the host at the next deploy-host.sh run. |
| 11 | CI actions pinned to major versions (@v4/@v5), not SHAs | Low | Fixed 2026-11-13: the workflow already pins full SHAs (checked in run 1, never recorded here). Verified against the GitHub API this run: checkout@11bd71901bbe5b1630ceea73d27597364c9af683 is genuine ("Prepare 4.2.2 Release (#1953)"); setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 and setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 both match their current tag tips (v5, v4). The checkout pin is v4.2.2, not the newest v4 tip; bumping it is currency, not a security fix, so it stays. |
| 12 | Agent service runs as root in its systemd unit (no User=); a compromise of the service is a compromise of the host user | High | Fixed: code-side in setup-host.sh (patchpilot system user, unit runs as it); applied on the live host 2026-11-13 in the Step 1 SSM session (useradd, systemd override, deploy-host.sh pulled 420ac33..3410f9b, health ok), verified by reading his SSM tab (memory/2026-11-13.md). CLOSED. |
| 13 | Security group SSH rule was 0.0.0.0/0 at launch; access is via SSM now, so the rule can be deleted | Medium | Corrected 2026-11-12: the 0.0.0.0/0 premise was wrong. His 2026-11-07 screenshot showed port 22 locked to a single IP (source starting 103.10), never 0.0.0.0/0, and he deleted the rule anyway that day at 17:55 PKT (memory/2026-11-07.md, line 19; item marked closed for good). Do not re-raise as a 0.0.0.0/0 finding. Resolved 2026-11-13: host-hardening-review.md section 3 no longer describes "22 from his IP"; the review and this audit now agree the rule is gone. |
| 14 | No unattended security updates or host firewall configured on the EC2 host | Low | Fixed: unattended-upgrades added to setup-host.sh; applied on the live host 2026-11-13 in the Step 1 SSM session (already newest, enabled, health ok). ufw deliberately deferred: it can break Docker networking, the security group is the inbound filter. CLOSED. |
| 15 | Attempt loop retries the same prompt 6 times with no feedback from the last attempt | Medium | Fixed 2026-11-14 (his call 2026-11-13: build in Phase 5): attempts 2-6 now get the previous attempt's exit code and a capped 2000-char log tail in the prompt (MAX_PROMPT_LOG_TAIL_CHARS); a syntax failure reports itself instead of an invented exit code; attempt 1 gets no feedback. TDD: 3 new tests (140 tests). Takes effect on the host at the next deploy-host.sh run; the fixture benchmark must be re-run after it to re-measure the 7/10 score honestly. CLOSED code-side; benchmark re-run is the founder's SSM step. |

## Failure drills

- LLM down: scripts/llm-down-drill.py, run 2026-11-12 (job
  19097591c863, real GitHub fetch, provider forced down). Result:
  PASS, job failed with "LLM provider is not configured, so no
  reproduction script could be generated. No verdict is claimed for
  this job." An earlier attempt hit the shared-egress unauthenticated
  rate limit and returned exit 2 (inconclusive), which the drill now
  reports distinctly. The same path was verified end to end over
  HTTP (job 88fb616c2091, POST /run 202, polled to failed) and the
  job and report pages render the reason (screenshots reviewed).
- GitHub rate-limited: faked 429 and 403-with-exhausted-quota
  responses at the client boundary (tests green), plus a live
  accidental proof: the drill's unauthenticated fetch was
  rate-limited by the shared egress IP and the pipeline reported
  SETUP_FAILED with "GitHub rate-limited the issue fetch; try again
  later", exactly the honest state the drill wants.
- Host down: frontend pointed at a stub agent returning 503 on
  POST /run (local Playwright run). Result: PASS, the job page shows
  "The agent service did not start this job..." with a retry button,
  zero page errors. The landing form already shows "Could not reach
  the agent service" on a dead agent URL (pre-existing, verified by
  code read; the submit path catches fetch failure).
- Takedown drill: scripts/takedown-drill.py, run 2026-11-12
  against a local backend (job bc50a032c4ae). Result: PASS, all 8
  checks (delete 403 without/wrong token, 204 with token, 404
  after, takedown-request 202, report untouched, 404 for unknown
  job, request recorded in .takedown-requests.jsonl).

## Host hardening review

See docs/deploy/host-hardening-review.md (written this run).
