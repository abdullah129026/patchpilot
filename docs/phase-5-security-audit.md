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
| 7 | A failed job's reason (job detail) is never shown on the job or report page; the user sees "failed" with no explanation | Medium | In progress (this run) |
| 8 | A job start that fails on the job page leaves the job visibly "queued" forever with no retry and no error | Medium | In progress (this run) |
| 9 | A job left "running" by a dead service process stays "running" forever; nothing marks it failed | Medium | Fixed: startup sweep marks stale running jobs failed with an honest detail (132 tests) |
| 10 | Base images pinned by tag only (python:3.12-slim, node:22-slim, gcc:13); a tag can move under the build | Medium | Open: digest pinning needs the digests fetched (see below) |
| 11 | CI actions pinned to major versions (@v4/@v5), not SHAs | Low | Open |
| 12 | Agent service runs as root in its systemd unit (no User=); a compromise of the service is a compromise of the host user | High | Open: unit fix is code-side, applying it on the live host is a founder SSM step |
| 13 | Security group SSH rule was 0.0.0.0/0 at launch; access is via SSM now, so the rule can be deleted | Medium | Open: founder console step (known since 2026-11-02) |
| 14 | No unattended security updates or host firewall configured on the EC2 host | Low | Open: founder console/SSM step |
| 15 | Attempt loop retries the same prompt 6 times with no feedback from the last attempt | Medium | Open: founder's call whether it lands in Phase 5 (carried from Phase 3) |

## Failure drills

- LLM down: local drill, backend with no provider configured.
  Result recorded in the run log.
- GitHub rate-limited: faked 403 rate-limit response at the client
  boundary plus a live-shaped pipeline drill. Result recorded below.
- Host down: frontend pointed at a dead agent URL (local Playwright
  run). Result recorded below.
- Takedown drill: local end-to-end delete + takedown-request drill.
  Result recorded below.

## Host hardening review

See docs/deploy/host-hardening-review.md (written this run).
