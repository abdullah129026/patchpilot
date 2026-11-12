// Sample jobs for the Phase 1 click path. Mirrors backend/app/fixtures.py.
// Real runs from the Phase 3 fixture suite (host run fixture-qwen7,
// 2026-11-06, Qwen3-Coder): the issue, error signature, and verdict are
// the recorded result for that issue. The reproduction script and failing
// test are the recorded minimal repro from scripts/fixture_issues.json,
// expressed as runnable code. No fix diff is shown on samples: the
// agent's suggested diff from the host run is not stored locally, and
// an unverified diff must never be presented as one.

export type Attempt = {
  n: number;
  exit_code: number | null;
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
  detail?: string;
  attempts: Attempt[];
  queue_position?: number;
  repro_script?: string | null;
  failing_test?: string | null;
  fix_diff?: string | null;
  fix_verified?: boolean;
};

export const FIXTURES: Job[] = [
  {
    id: "sample-humanize-57",
    status: "done",
    verdict: "REPRODUCED",
    fixture: true,
    issue: { owner: "python-humanize", repo: "humanize", number: 57 },
    stack: "python",
    signature: "ValueError: math domain error",
    attempts: [
      {
        n: 1,
        exit_code: 1,
        log: "ValueError: math domain error\n",
        script: "import humanize\n\nprint(humanize.metric(0))\n",
      },
    ],
    repro_script: "import humanize\n\nprint(humanize.metric(0))\n",
    failing_test: "import humanize\n\n\ndef test_metric_zero():\n    humanize.metric(0)\n",
    fix_diff: null,
    fix_verified: false,
  },
  {
    id: "sample-pyflakes-764",
    status: "done",
    verdict: "REPRODUCED",
    fixture: true,
    issue: { owner: "PyCQA", repo: "pyflakes", number: 764 },
    stack: "python",
    signature: "TypeError: 'bool' object is not subscriptable",
    attempts: [
      {
        n: 1,
        exit_code: 1,
        log: "TypeError: 'bool' object is not subscriptable\n",
        script:
          'from pyflakes.api import check\n\ncheck("x: int\\nx.__dict__\\ndef f(): x = 1\\n")\n',
      },
    ],
    repro_script:
      'from pyflakes.api import check\n\ncheck("x: int\\nx.__dict__\\ndef f(): x = 1\\n")\n',
    failing_test:
      'from pyflakes.api import check\n\n\ndef test_annotated_name_lookup():\n    check("x: int\\nx.__dict__\\ndef f(): x = 1\\n")\n',
    fix_diff: null,
    fix_verified: false,
  },
  {
    id: "sample-pyflakes-744",
    status: "done",
    verdict: "NOT_REPRODUCED",
    fixture: true,
    issue: { owner: "PyCQA", repo: "pyflakes", number: 744 },
    stack: "python",
    signature: "AttributeError: 'Name' object has no attribute '_pyflakes_parent'",
    attempts: [
      {
        n: 1,
        exit_code: 0,
        log: "No output contained the reported error.\n",
        script: 'from pyflakes.api import check\n\ncheck("print *= -1\\n")\n',
      },
    ],
    repro_script: 'from pyflakes.api import check\n\ncheck("print *= -1\\n")\n',
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
