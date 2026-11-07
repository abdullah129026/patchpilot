import Link from "next/link";
import JobForm from "@/components/JobForm";
import TrackEvent from "@/components/TrackEvent";
import { VerdictBadge } from "@/components/ui";

const VERDICTS = [
  {
    name: "REPRODUCED",
    text: "The reported error showed up in the sandbox, with the log to prove it.",
  },
  {
    name: "NOT_REPRODUCED",
    text: "The bug did not show up here. An honest negative, with everything that was tried.",
  },
  {
    name: "SETUP_FAILED",
    text: "The environment could not be built, so no attempt was possible.",
  },
  {
    name: "ISSUE_UNDERSPECIFIED",
    text: "The issue lacks the error, steps, or expected behavior needed to reproduce it.",
  },
  {
    name: "LIMIT_REACHED",
    text: "A ceiling stopped the job: attempts, time, or the daily job cap.",
  },
];

export default function Home() {
  return (
    <>
      <TrackEvent event="landing_view" />
      <section className="hero">
        <h1>Your issue says it crashes. PatchPilot proves it.</h1>
        <p className="lede">
          Paste a public GitHub issue link. PatchPilot reproduces the bug in a
          Docker sandbox and returns a reproduction script, a failing test, and
          a suggested fix diff, with the captured logs as proof. The lead
          artifact is the failing test reporters never send.
        </p>
        <JobForm />
        <p className="form-note">
          Public repositories only. Python, JavaScript, and C++ in v1. No
          accounts, no billing. Jobs run one at a time with a daily cap.
        </p>
      </section>

      <h2 id="how-it-works">How it works</h2>
      <div className="grid">
        <div className="card">
          <h3>1. Paste the issue</h3>
          <p>A public GitHub issue URL. The error signature is extracted before any compute is spent.</p>
        </div>
        <div className="card">
          <h3>2. Watch it run</h3>
          <p>Setup, then up to six attempts in a capped container: network on to install, network off to run.</p>
        </div>
        <div className="card">
          <h3>3. Read the verdict</h3>
          <p>Computed from exit codes and log matches, never written by the model. The raw log is one click away.</p>
        </div>
        <div className="card">
          <h3>4. Take the evidence</h3>
          <p>Copy the reproduction script and the failing test. The fix diff is a suggestion, labeled as one.</p>
        </div>
      </div>

      <h2>Five verdicts, no success theater</h2>
      <p>
        A tool that only ever says “reproduced” cannot be trusted. Every job
        ends in one of five verdicts, including the uncomfortable ones.
      </p>
      <div className="grid">
        {VERDICTS.map((v) => (
          <div className="card" key={v.name}>
            <VerdictBadge verdict={v.name} />
            <p style={{ marginTop: 10 }}>{v.text}</p>
          </div>
        ))}
      </div>

      <h2 id="samples">Sample reports</h2>
      <p>
        Real runs from the fixture suite (2026-11-06, Qwen3-Coder): seven of
        ten curated issues reproduced. These three show the shape of a
        report, hits and miss included. The{" "}
        <Link href="/case-study">case study</Link> has the full distribution.
      </p>
      <div className="grid">
        <div className="card">
          <h3>Reproduced: humanize #57</h3>
          <p>
            <VerdictBadge verdict="REPRODUCED" /> ValueError: math domain
            error, matched in the captured log.
          </p>
          <p>
            <Link href="/report/sample-humanize-57">Read the report</Link> ·{" "}
            <Link href="/jobs/sample-humanize-57">See the job run</Link>
          </p>
        </div>
        <div className="card">
          <h3>Reproduced: pyflakes #764</h3>
          <p>
            <VerdictBadge verdict="REPRODUCED" /> TypeError: &apos;bool&apos;
            object is not subscriptable.
          </p>
          <p>
            <Link href="/report/sample-pyflakes-764">Read the report</Link> ·{" "}
            <Link href="/jobs/sample-pyflakes-764">See the job run</Link>
          </p>
        </div>
        <div className="card">
          <h3>Not reproduced: pyflakes #744</h3>
          <p>
            <VerdictBadge verdict="NOT_REPRODUCED" /> Every attempt ran clean.
            The negative outcome, shown in full.
          </p>
          <p>
            <Link href="/report/sample-pyflakes-744">Read the report</Link> ·{" "}
            <Link href="/jobs/sample-pyflakes-744">See the job run</Link>
          </p>
        </div>
      </div>

      <h2>Trust block</h2>
      <div className="panel">
        <ul className="tight">
          <li>Nothing is ever posted to your repository. No PRs, no comments.</li>
          <li>Every report discloses that an AI agent produced it, and separates what was verified from what was suggested.</li>
          <li>Untrusted code runs only inside a capped Docker container, destroyed after the job. Job workspaces are deleted after each job.</li>
          <li>Issue text and repo files are treated as data, never as instructions to the agent.</li>
          <li>Reports are kept and removed on request. See the <Link href="/privacy">privacy note</Link>.</li>
        </ul>
      </div>

      <h2>Limits, stated plainly</h2>
      <p>
        Three languages (Python, JavaScript, C++). Public repos only. One job at
        a time, with a daily job ceiling while the demo runs on a small
        inference budget. A suggested fix is never claimed correct beyond the
        one verified test transition on its report.
      </p>
    </>
  );
}
