"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getFixture, issueUrl, type Job } from "@/lib/fixtures";
import {
  CodeBlock,
  CopyButton,
  LogBlock,
  VerdictBadge,
  VerdictExplanation,
} from "@/components/ui";

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
    loadJob(params.id).then(setJob);
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
              Sample report. Synthetic data, fictional repository, built to show
              the report shape. Nothing here claims a real reproduction.
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
            The matched error lines below come from attempt {matchedLog.n} of
            this job, captured inside the sandbox.
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
            <CopyButton text={job.repro_script} label="Copy script" />
          </p>
          <CodeBlock code={job.repro_script} />
        </>
      )}

      {job.failing_test && (
        <>
          <h2>Failing test</h2>
          <p>
            This test failed before the fix and passed after it, inside the
            sandbox. That transition is what the verified label below rests on.
          </p>
          <p>
            <CopyButton text={job.failing_test} label="Copy test" />
          </p>
          <CodeBlock code={job.failing_test} />
        </>
      )}

      {job.fix_diff && (
        <div className="panel suggestion" style={{ marginTop: 32 }}>
          <h3>AI suggestion: fix diff</h3>
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
        </div>
      )}
    </>
  );
}
