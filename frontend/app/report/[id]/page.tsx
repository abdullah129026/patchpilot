"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getFixture, issueUrl, type Job } from "@/lib/fixtures";
import { track } from "@/lib/analytics";
import {
  CodeBlock,
  CopyButton,
  LogBlock,
  VerdictBadge,
  VerdictExplanation,
} from "@/components/ui";
import Takedown from "@/components/Takedown";

async function loadJob(id: string): Promise<Job | null> {
  const fixture = getFixture(id);
  if (fixture) return fixture;
  const agentUrl = process.env.NEXT_PUBLIC_AGENT_URL;
  if (!agentUrl) return null;
  try {
    const res = await fetch(`${agentUrl}/api/jobs/${id}`);
    if (!res.ok) return null;
    return (await res.json()) as Job;
  } catch {
    return null;
  }
}

export default function ReportPage({ params }: { params: { id: string } }) {
  const [job, setJob] = useState<Job | null | undefined>(undefined);

  useEffect(() => {
    loadJob(params.id).then((loaded) => {
      setJob(loaded);
      if (!loaded) return;
      if (loaded.verdict) track("verdict_shown", loaded.verdict);
      if (loaded.fixture) track("sample_report_opened");
    });
  }, [params.id]);

  if (job === undefined) return <p style={{ marginTop: 40 }}>Loading report…</p>;
  if (job === null)
    return (
      <div style={{ marginTop: 40 }}>
        <h1>Report not found</h1>
        <p>
          No report with this id exists. <Link href="/">Back to the landing page</Link>.
        </p>
      </div>
    );

  const matchedLog = job.attempts.find(
    (a) => job.signature && a.log.includes(job.signature)
  );

  return (
    <>
      <section style={{ marginTop: 40 }}>
        {job.fixture && (
          <div className="notice">
            <p>
              Sample report from the fixture suite run on 2026-11-06
              (Qwen3-Coder, 7 of 10 reproduced). The issue, error, and
              verdict are from the real run; the script and test are the
              recorded reproduction from the fixture. No fix diff is shown:
              the run&apos;s suggested diff is not stored here.{" "}
              <Link href="/case-study">Read the case study</Link>.
            </p>
          </div>
        )}
        <p className="small">
          Report for{" "}
          <a href={issueUrl(job)} target="_blank" rel="noreferrer">
            {job.issue.owner}/{job.issue.repo} #{job.issue.number}
          </a>
        </p>
        <h1>
          {job.verdict ? (
            <VerdictBadge verdict={job.verdict} />
          ) : (
            "Verdict pending"
          )}
        </h1>
        {job.verdict && <VerdictExplanation verdict={job.verdict} />}
        <dl className="kv">
          <dt>Issue</dt>
          <dd>
            <a href={issueUrl(job)} target="_blank" rel="noreferrer">
              {issueUrl(job)}
            </a>
          </dd>
          {job.stack && (
            <>
              <dt>Stack</dt>
              <dd>{job.stack}</dd>
            </>
          )}
          {job.signature && (
            <>
              <dt>Error signature</dt>
              <dd>
                <code>{job.signature}</code>
              </dd>
            </>
          )}
          <dt>Attempts</dt>
          <dd>{job.attempts.length}</dd>
        </dl>
        <p className="small">
          Verdict computed from run evidence (exit codes, signature match, test
          transitions). AI output on this page is labeled as a suggestion and
          never gates the verdict. <Link href={`/jobs/${job.id}`}>See the job run</Link>.
        </p>
      </section>

      <h2>Evidence</h2>
      {matchedLog ? (
        <>
          <p>
            {job.fixture
              ? "The matched error line below is from attempt 1 of this job, from the fixture suite run."
              : "The matched error lines below come from attempt 1 of this job, captured inside the sandbox."}
          </p>
          <LogBlock log={matchedLog.log} />
        </>
      ) : (
        <p>
          No attempt produced the reported error. The full attempt logs are on
          the <Link href={`/jobs/${job.id}`}>job page</Link>.
        </p>
      )}

      {job.repro_script && (
        <>
          <h2>Reproduction script</h2>
          <p>
            <CopyButton
              text={job.repro_script}
              label="Copy script"
              event="report_copied_script"
            />
          </p>
          <CodeBlock code={job.repro_script} />
        </>
      )}

      {job.failing_test && (
        <>
          <h2>Failing test</h2>
          <p>
            {job.fixture
              ? "This test expresses the recorded reproduction. During fixture curation it failed at the base commit and passed at the fix commit."
              : "This test failed before the fix and passed after it, inside the sandbox. That transition is what the verified label below rests on."}
          </p>
          <p>
            <CopyButton
              text={job.failing_test}
              label="Copy test"
              event="report_copied_test"
            />
          </p>
          <CodeBlock code={job.failing_test} />
        </>
      )}

      {job.fix_diff && (
        <details
          className="panel suggestion"
          style={{ marginTop: 32 }}
          onToggle={(event) => {
            if ((event.target as HTMLDetailsElement).open) {
              track("diff_expanded");
            }
          }}
        >
          <summary>
            <h3 style={{ display: "inline" }}>AI suggestion: fix diff</h3>
          </summary>
          <p>
            This diff was proposed by the agent. It is a suggestion, not a
            verified correction, unless the label says otherwise.{" "}
            {job.fix_verified ? (
              <strong>VERIFIED: the failing test passed after this diff was applied.</strong>
            ) : (
              <strong>Not verified.</strong>
            )}
          </p>
          <CodeBlock code={job.fix_diff} />
        </details>
      )}

      <Takedown jobId={job.id} fixture={job.fixture} />
    </>
  );
}
