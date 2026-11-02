"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getFixture, issueUrl, type Job } from "@/lib/fixtures";
import { LogBlock, VerdictBadge } from "@/components/ui";

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

export default function JobPage({ params }: { params: { id: string } }) {
  const [job, setJob] = useState<Job | null | undefined>(undefined);

  useEffect(() => {
    loadJob(params.id).then(setJob);
  }, [params.id]);

  if (job === undefined) return <p style={{ marginTop: 40 }}>Loading job…</p>;
  if (job === null)
    return (
      <div style={{ marginTop: 40 }}>
        <h1>Job not found</h1>
        <p>
          No job with this id exists, or the agent service is not reachable
          from this build. <Link href="/">Back to the landing page</Link>.
        </p>
      </div>
    );

  return (
    <>
      <section style={{ marginTop: 40 }}>
        <p className="small">
          Job <span className="mono">{job.id}</span>
          {job.fixture && " · sample job, synthetic data"}
        </p>
        <h1>
          <a href={issueUrl(job)} target="_blank" rel="noreferrer">
            {job.issue.owner}/{job.issue.repo} #{job.issue.number}
          </a>
        </h1>
        <div className="badge-row">
          <span className="verdict">{job.status}</span>
          {job.verdict && <VerdictBadge verdict={job.verdict} />}
          {job.stack && <span className="verdict">{job.stack}</span>}
        </div>
        {job.signature && (
          <p>
            Expected error signature:{" "}
            <code>{job.signature}</code>
          </p>
        )}
        {job.status === "queued" && (
          <div className="notice">
            <p>
              This job is queued. The reproduction runner arrives in Phase 3;
              until then, submitted jobs wait here rather than pretending to
              run. Sample jobs show the full click path:{" "}
              <Link href="/jobs/fixture-reproduced">fixture-reproduced</Link>.
            </p>
          </div>
        )}
        {job.status === "done" && (
          <p>
            <Link href={`/report/${job.id}`}>Read the full report →</Link>
          </p>
        )}
      </section>

      <h2>Attempts</h2>
      {job.attempts.length === 0 && (
        <p className="small">No attempts recorded yet.</p>
      )}
      {job.attempts.map((attempt) => (
        <div className="attempt" key={attempt.n}>
          <h3>
            Attempt {attempt.n} · exit code {attempt.exit_code}
          </h3>
          <LogBlock log={attempt.log} />
        </div>
      ))}
    </>
  );
}
