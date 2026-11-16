import Link from "next/link";
import { VerdictBadge } from "@/components/ui";

const RESULTS = [
  { owner: "PyCQA", repo: "pyflakes", number: 764, first: "REPRODUCED", latest: "REPRODUCED", signature: "TypeError: 'bool' object is not subscriptable" },
  { owner: "PyCQA", repo: "pyflakes", number: 834, first: "REPRODUCED", latest: "NOT_REPRODUCED", signature: "AttributeError: 'ClassScope' object has no attribute 'indirect_assignments'" },
  { owner: "asottile", repo: "pyupgrade", number: 194, first: "REPRODUCED", latest: "NOT_REPRODUCED", signature: "ValueError: Single '{' encountered in format string" },
  { owner: "pypa", repo: "packaging", number: 638, first: "REPRODUCED", latest: "NOT_REPRODUCED", signature: "TypeError: expected string or bytes-like object" },
  { owner: "python-humanize", repo: "humanize", number: 17, first: "REPRODUCED", latest: "REPRODUCED", signature: "TypeError: can't subtract offset-naive and offset-aware datetimes" },
  { owner: "python-humanize", repo: "humanize", number: 57, first: "REPRODUCED", latest: "NOT_REPRODUCED", signature: "ValueError: math domain error" },
  { owner: "python-humanize", repo: "humanize", number: 122, first: "REPRODUCED", latest: "REPRODUCED", signature: "TypeError: can't subtract offset-naive and offset-aware datetimes" },
  { owner: "PyCQA", repo: "pyflakes", number: 744, first: "NOT_REPRODUCED", latest: "NOT_REPRODUCED", signature: "AttributeError: 'Name' object has no attribute '_pyflakes_parent'" },
  { owner: "asottile", repo: "pyupgrade", number: 437, first: "NOT_REPRODUCED", latest: "NOT_REPRODUCED", signature: "KeyError: (3, 11)" },
  { owner: "python-humanize", repo: "humanize", number: 62, first: "NOT_REPRODUCED", latest: "NOT_REPRODUCED", signature: "ValueError: cannot convert float NaN to integer" },
];

export default function CaseStudy() {
  return (
    <>
      <section style={{ marginTop: 40 }}>
        <p className="small">Case study · latest measured run · 2026-11-15</p>
        <h1>Three of ten real bugs, reproduced. Seven missed, shown too.</h1>
        <p className="lede">
          PatchPilot ran ten curated Python issues from real public repos
          through the full pipeline on its own host: fetch the issue, clone
          the repo at the commit before the fix, generate a reproduction
          script, run it in a capped Docker container, and compute the
          verdict from the exit code and the error match. Nothing here is a
          demo script. This page leads with the latest measurement, a re-run
          on 2026-11-15 after the attempt feedback loop was added. The first
          run, on 2026-11-06, scored 7 of 10. That number no longer
          describes the current code, and it is kept below as history, not
          as the headline. The misses are listed alongside the hits because
          a tool that only shows hits cannot be trusted.
        </p>
        <dl className="kv">
          <dt>Model</dt>
          <dd>Qwen3-Coder-30B, via Amazon Bedrock</dd>
          <dt>Latest run</dt>
          <dd>fixture re-run, 2026-11-15, EC2 host, attempt feedback loop live</dd>
          <dt>Result</dt>
          <dd>3 REPRODUCED, 7 NOT_REPRODUCED, 0 setup failures, 0 errors</dd>
          <dt>First run</dt>
          <dd>fixture-qwen7, 2026-11-06 20:21 PKT, EC2 host: 7 REPRODUCED, 3 NOT_REPRODUCED</dd>
          <dt>Target</dt>
          <dd>At least 3 of 10, set in the Phase 0 plan. Met, with no margin.</dd>
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

      <h2>The ten, with verdicts from both runs</h2>
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
            first run <VerdictBadge verdict={r.first} /> latest run{" "}
            <VerdictBadge verdict={r.latest} />{" "}
            <code>{r.signature}</code>
          </li>
        ))}
      </ul>

      <h2>The re-run, and what changed</h2>
      <p>
        The attempt loop used to retry the identical prompt up to six times,
        with no feedback from the previous attempt. In Phase 5 the loop was
        changed: attempts 2 to 6 now get the previous attempt&apos;s exit code
        and a capped tail of its log in the prompt. The loop changed how the
        code behaves, so the old score stopped describing the current code
        and the suite was re-run on the same ten fixtures, at the same
        pinned pre-fix commits, on 2026-11-15.
      </p>
      <p>
        The re-run scored 3 of 10. Four issues that reproduced in the first
        run did not reproduce this time (pyflakes #834, pyupgrade #194,
        packaging #638, humanize #57), and no issue that missed before
        reproduced this time. The loop did not lift the score on this run.
        Causation is not proven: this is one run against one run, the model
        samples, and attempt 1, which carries no feedback, plainly failed
        this time on fixtures it has passed before. What is proven is
        narrower and it is enough to act on: no score above 3 of 10 can
        honestly be claimed for the loop version until another measurement
        says otherwise.
      </p>

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
        setup failures. The 7 of 10 run was the first fair measurement, and
        it stood as the headline until the 2026-11-15 re-run superseded it.
        None of the invalidated runs is quoted as a model result anywhere.
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
          met the target on the first run and again, with no margin, on the
          re-run.
        </li>
        <li>
          The seven misses are real. The attempt feedback loop, the
          clearest known improvement, is built and live, and the first
          measurement with it scored 3 of 10. Whether the loop helped,
          hurt, or neither is still an open question: the next experiment
          is to revert it and re-run, or run the suite once more unchanged
          to size the run-to-run variance.
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
        <Link href="/#samples">Sample reports</Link> from the first run, two
        reproduced and one missed, with the script and test for each. The
        fixture list and the curation rules live in the repo.
      </p>
    </>
  );
}
