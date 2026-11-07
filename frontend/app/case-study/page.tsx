import Link from "next/link";
import { VerdictBadge } from "@/components/ui";

const RESULTS = [
  { owner: "PyCQA", repo: "pyflakes", number: 764, verdict: "REPRODUCED", signature: "TypeError: 'bool' object is not subscriptable" },
  { owner: "PyCQA", repo: "pyflakes", number: 834, verdict: "REPRODUCED", signature: "AttributeError: 'ClassScope' object has no attribute 'indirect_assignments'" },
  { owner: "asottile", repo: "pyupgrade", number: 194, verdict: "REPRODUCED", signature: "ValueError: Single '{' encountered in format string" },
  { owner: "pypa", repo: "packaging", number: 638, verdict: "REPRODUCED", signature: "TypeError: expected string or bytes-like object" },
  { owner: "python-humanize", repo: "humanize", number: 17, verdict: "REPRODUCED", signature: "TypeError: can't subtract offset-naive and offset-aware datetimes" },
  { owner: "python-humanize", repo: "humanize", number: 57, verdict: "REPRODUCED", signature: "ValueError: math domain error" },
  { owner: "python-humanize", repo: "humanize", number: 122, verdict: "REPRODUCED", signature: "TypeError: can't subtract offset-naive and offset-aware datetimes" },
  { owner: "PyCQA", repo: "pyflakes", number: 744, verdict: "NOT_REPRODUCED", signature: "AttributeError: 'Name' object has no attribute '_pyflakes_parent'" },
  { owner: "asottile", repo: "pyupgrade", number: 437, verdict: "NOT_REPRODUCED", signature: "KeyError: (3, 11)" },
  { owner: "python-humanize", repo: "humanize", number: 62, verdict: "NOT_REPRODUCED", signature: "ValueError: cannot convert float NaN to integer" },
];

export default function CaseStudy() {
  return (
    <>
      <section style={{ marginTop: 40 }}>
        <p className="small">Case study · first measured run · 2026-11-06</p>
        <h1>Seven of ten real bugs, reproduced. Three missed, shown too.</h1>
        <p className="lede">
          PatchPilot ran ten curated Python issues from real public repos
          through the full pipeline on its own host: fetch the issue, clone
          the repo at the commit before the fix, generate a reproduction
          script, run it in a capped Docker container, and compute the
          verdict from the exit code and the error match. Nothing here is a
          demo script. The misses are listed alongside the hits because a
          tool that only shows hits cannot be trusted.
        </p>
        <dl className="kv">
          <dt>Model</dt>
          <dd>Qwen3-Coder-30B, via Amazon Bedrock</dd>
          <dt>Run</dt>
          <dd>fixture-qwen7, 2026-11-06 20:21 PKT, EC2 host</dd>
          <dt>Result</dt>
          <dd>7 REPRODUCED, 3 NOT_REPRODUCED, 0 setup failures, 0 errors</dd>
          <dt>Target</dt>
          <dd>At least 3 of 10, set in the Phase 0 plan</dd>
        </dl>
      </section>

      <h2>How the ten were picked</h2>
      <p>
        Each fixture is a real issue with a merged fix. Before the run, every
        one was checked twice by hand: the recorded error occurs at the base
        commit (the first parent of the fix merge) and does not occur at the
        fix commit. Issues that failed that check were rejected and recorded
        in the repo. The run then had to reproduce the bug from the issue
        text alone, starting at the base commit, with no knowledge of the
        fix.
      </p>

      <h2>The ten, with verdicts</h2>
      <ul className="tight">
        {RESULTS.map((r) => (
          <li key={`${r.owner}/${r.repo}#${r.number}`}>
            <a
              href={`https://github.com/${r.owner}/${r.repo}/issues/${r.number}`}
              target="_blank"
              rel="noreferrer"
            >
              {r.owner}/{r.repo} #{r.number}
            </a>{" "}
            <VerdictBadge verdict={r.verdict} />{" "}
            <code>{r.signature}</code>
          </li>
        ))}
      </ul>

      <h2>The run that counted was the seventh</h2>
      <p>
        Six earlier runs were invalidated by real bugs the live host exposed
        and unit tests could not see, because tests fake the exact
        boundaries that failed. Each was fixed, one commit each, before the
        next run:
      </p>
      <ul className="tight">
        <li>The Bedrock client was built with no region, so every model call died before it started.</li>
        <li>Model replies arrive wrapped in markdown fences, and the raw reply was written as the script, so all sixty attempts failed the syntax check with zero container runs spent.</li>
        <li>A relative workspace path was passed to Docker as a volume name, so all sixty attempts exited 125.</li>
        <li>Installs happened in a disposable container and never reached the run container, so the target package was never importable.</li>
        <li>Container root could not write into the workspace, so all ten jobs failed setup.</li>
        <li>VCS-versioned projects could not build without git in the slim image, so all four humanize jobs failed setup.</li>
      </ul>
      <p>
        An intermediate fair run before the last fix scored 3 of 10 with 4
        setup failures. The 7 of 10 run supersedes it. None of the
        invalidated runs is quoted as a model result anywhere.
      </p>

      <h2>The malicious-issue drill passed</h2>
      <p>
        A crafted issue ordering the agent to curl an external URL and
        exfiltrate /etc/passwd went through the real pipeline on the host
        the same evening. The job verdict was REPRODUCED on the crafted bug,
        and the only commands that reached the executor were the repro
        script and the test run. No injected text reached the executor.
      </p>

      <h2>What is not claimed</h2>
      <ul className="tight">
        <li>
          The head-to-head against Claude Haiku 5.5 never ran. The account
          returns AccessDenied for that model, so only Qwen is measured.
          Qwen is the default because it is the only measured model, and it
          beat the target.
        </li>
        <li>
          The three misses are real. The attempt loop retries the identical
          prompt up to six times with no feedback from the previous
          attempt&apos;s log. Feeding the last error back in is the clearest
          known improvement and the likely lever for those three.
        </li>
        <li>
          JS and C++ reproduction paths are built and unit-tested, but the
          live fixture proof so far is Python only.
        </li>
        <li>
          ISSUE_UNDERSPECIFIED and LIMIT_REACHED are covered by unit tests
          only; they have not been seen live.
        </li>
      </ul>

      <h2>See the evidence</h2>
      <p>
        <Link href="/#samples">Sample reports</Link> from this run, two
        reproduced and one missed, with the script and test for each. The
        fixture list and the curation rules live in the repo.
      </p>
    </>
  );
}
