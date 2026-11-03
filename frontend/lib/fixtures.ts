// Fixture jobs for the Phase 1 click path. Mirrors backend/app/fixtures.py.
// Synthetic examples, clearly flagged. Nothing here claims a real
// reproduction: the repo names are fictional.

export type Attempt = {
  n: number;
  exit_code: number;
  log: string;
  script: string;
};

export type Job = {
  id: string;
  status: string;
  verdict: string | null;
  fixture?: boolean;
  issue: { owner: string; repo: string; number: number };
  stack?: string;
  signature?: string;
  attempts: Attempt[];
  queue_position?: number;
  repro_script?: string | null;
  failing_test?: string | null;
  fix_diff?: string | null;
  fix_verified?: boolean;
};

export const FIXTURES: Job[] = [
  {
    id: "fixture-reproduced",
    status: "done",
    verdict: "REPRODUCED",
    fixture: true,
    issue: { owner: "fixture", repo: "demo-python-app", number: 42 },
    stack: "python",
    signature: "ValueError: bad key",
    attempts: [
      {
        n: 1,
        exit_code: 1,
        log: "Traceback (most recent call last):\nValueError: bad key\n",
        script: 'config = {}\nprint(config["missing"])\n',
      },
    ],
    repro_script: 'config = {}\nprint(config["missing"])\n',
    failing_test: "def test_missing_key():\n    assert load_config({}) is not None\n",
    fix_diff:
      "--- a/config.py\n+++ b/config.py\n-    return data[key]\n+    return data.get(key)\n",
    fix_verified: true,
  },
  {
    id: "fixture-not-reproduced",
    status: "done",
    verdict: "NOT_REPRODUCED",
    fixture: true,
    issue: { owner: "fixture", repo: "demo-python-app", number: 43 },
    stack: "python",
    signature: "KeyError: missing",
    attempts: [{ n: 1, exit_code: 0, log: "ok\n", script: "print('ok')\n" }],
    repro_script: null,
    failing_test: null,
    fix_diff: null,
    fix_verified: false,
  },
];

export function getFixture(id: string): Job | undefined {
  return FIXTURES.find((job) => job.id === id);
}

export function issueUrl(job: Job): string {
  return `https://github.com/${job.issue.owner}/${job.issue.repo}/issues/${job.issue.number}`;
}

export const VERDICT_EXPLANATIONS: Record<string, string> = {
  REPRODUCED:
    "The error signature from the issue appeared in a captured sandbox run. The reproduction script and failing test below are the evidence.",
  NOT_REPRODUCED:
    "Every attempt ran without producing the reported error. This is a real outcome, not a failure of the report: it says the bug did not show up here.",
  SETUP_FAILED:
    "The environment could not be built, so no reproduction attempt was possible. The setup log is the evidence.",
  ISSUE_UNDERSPECIFIED:
    "The issue does not contain enough information to reproduce it: no clear error, no steps, or no expected behavior.",
  LIMIT_REACHED:
    "The job hit a ceiling (attempts, time, or the daily job cap) before reaching a verdict. The stop reason is recorded on the job.",
};
