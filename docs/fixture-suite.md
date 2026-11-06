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

## How a fixture runs

A fixture job runs the repo at `base_commit`, the first parent of
the fix merge, not at HEAD: at HEAD the bug is already fixed and
nothing could reproduce. `scripts/run-fixture-suite.py` passes
`base_commit` as the job's `ref`; the pipeline checks it out with
`github_client.checkout_ref` after the depth-1 clone (GitHub serves
a fetch by full SHA). Public jobs never carry a ref and run HEAD.

Results are published either way in the Phase 4 case study,
including failures. No entry is recorded from memory: each one is
fetched and checked first.

## The 10 (curated and verified 2026-11-05)

Each entry in `scripts/fixture_issues.json` was verified locally:
at `base_commit` the quoted error occurs, at `fix_commit` it does
not; and the repo's own analyzer extracts exactly the recorded
`error_signature` from the live issue body. Verification harness and
per-fixture repros live in the goal hidden_files under
`fixture-verify/`.

| Issue | Error | Fix PR |
| --- | --- | --- |
| python-humanize/humanize#57 | `ValueError: math domain error` | #47 |
| python-humanize/humanize#62 | `ValueError: cannot convert float NaN to integer` | #63 |
| python-humanize/humanize#17 | `TypeError: can't subtract offset-naive and offset-aware datetimes` | #100 |
| python-humanize/humanize#122 | `TypeError: can't subtract offset-naive and offset-aware datetimes` | #123 |
| pypa/packaging#638 | `TypeError: expected string or bytes-like object` | #650 |
| PyCQA/pyflakes#744 | `AttributeError: 'Name' object has no attribute '_pyflakes_parent'` | #745 |
| PyCQA/pyflakes#764 | `TypeError: 'bool' object is not subscriptable` | #765 |
| PyCQA/pyflakes#834 | `AttributeError: 'ClassScope' object has no attribute 'indirect_assignments'` | #836 |
| asottile/pyupgrade#194 | `ValueError: Single '{' encountered in format string` | #195 |
| asottile/pyupgrade#437 | `KeyError: (3, 11)` | #438 |

## Checked and rejected

- more-itertools#485: the issue has two cases; PR #486 fixed only
  the first, while the analyzer extracts the second case's error
  line, so the signature would not match a faithful repro.
- more-itertools#1250, #1282: the bug swallows the error, so no
  repro exits non-zero; the matcher cannot score them.
- more-itertools#1300: the fix only rewords an error message.
- more-itertools#1215: docs-only fix, the error still raises.
- dbader/schedule#125: the quoted message is Python 2 wording;
  on Python 3.12 the same failure reads differently, so the
  signature would not match the log.
- asottile/pyupgrade#312: the fix is a refusal to rewrite, and the
  natural failing test does not pass after it.
- pypa/packaging#928: `InvalidLicenseExpression` does not end in
  `Error`/`Exception`, so the analyzer extracts no signature.
- pypa/packaging#1154: the body quotes no error line at all.
- Delgan/loguru#1450: loguru catches the KeyError internally and
  the process exits 0, so no repro can match.

## Running the suite (on the EC2 host, needs Docker + Bedrock)

```sh
cd patchpilot
PATCHPILOT_BEDROCK_MODEL_ID=anthropic.claude-haiku-5-5 \
  python scripts/run-fixture-suite.py scripts/fixture_issues.json
# then swap the model id to qwen.qwen3-coder-30b-a3b-v1:0 and run again
```

The model id is printed at the top of each run, so the two runs
arbitrate D8 on the same 10 issues. The runner exits 0 only when at
least 3 of 10 reproduce. The full guided-session runbook (deploy,
both runs, verdict-path check, malicious drill) is
docs/deploy/phase-3-host-runbook.md.
