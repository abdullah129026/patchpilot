# Fixture suite (Phase 3)

The suite is 10 curated Python issues from small public repos. An
issue qualifies only when all of these have been verified live
against the GitHub API before it is recorded:

1. The issue is closed, with a merged fix commit linked from it.
2. The repo is public, small enough to clone under the 500 MB cap,
   and installs with pip from requirements.txt or pyproject.toml.
3. The issue body quotes an error line the deterministic matcher can
   match (otherwise it is ISSUE_UNDERSPECIFIED by design, not a
   fixture for reproduction).
4. Reverting the fix commit reintroduces the quoted error, so the
   reproduction is checkable against reality, not against the report.

Results are published either way in the Phase 4 case study,
including failures. No entry is recorded from memory: each one is
fetched and checked first. Curation is in progress; the runner is
`scripts/run-fixture-suite.py`.
