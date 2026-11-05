"use client";

import { useEffect, useRef, useState } from "react";
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
  const startedRef = useRef(false);

  useEffect(() => {
    let stopped = false;
    let source: EventSource | null = null;
    let timer: ReturnType<typeof setInterval> | null = null;
    const agentUrl = process.env.NEXT_PUBLIC_AGENT_URL;

    async function watch(id: string) {
      const loaded = await loadJob(id);
      if (stopped) return;
      setJob(loaded);
      if (!loaded || loaded.fixture || !agentUrl) return;
      // A real queued job starts itself: the run endpoint returns
      // 202 at once and the job runs in the background.
      if (loaded.status === "queued" && !startedRef.current) {
        startedRef.current = true;
        try {
          const res = await fetch(`${agentUrl}/api/jobs/${id}/run`, {
            method: "POST",
          });
          if (res.ok) setJob(await res.json());
        } catch {
          // The poll below still shows the job; a failed start is
          // visible as a job stuck in queued.
        }
      }
      if (loaded.status === "done" || loaded.status === "failed") return;
      const poll = () => {
        timer = setInterval(async () => {
          const current = await loadJob(id);
          if (!stopped && current) setJob(current);
          if (current && (current.status === "done" || current.status === "failed") && timer) {
            clearInterval(timer);
          }
        }, 2000);
      };
      try {
        source = new EventSource(`${agentUrl}/api/jobs/${id}/stream`);
        source.onmessage = (event) => {
          const current = JSON.parse(event.data) as Job;
          setJob(current);
          if (current.status === "done" || current.status === "failed") {
            source?.close();
          }
        };
        source.onerror = () => {
          source?.close();
          source = null;
          poll();
        };
      } catch {
        poll();
      }
    }

    watch(params.id);
    return () => {
      stopped = true;
      source?.close();
      if (timer) clearInterval(timer);
    };
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
              This job is queued and starts automatically; one job runs at
              a time. Sample jobs show the full click path:{" "}
              <Link href="/jobs/fixture-reproduced">fixture-reproduced</Link>.
              {job.queue_position !== undefined && job.queue_position > 1 && (
                <>
                  {" "}Position {job.queue_position} in the queue.
                </>
              )}
            </p>
          </div>
        )}
        {job.status === "running" && (
          <div className="notice">
            <p>
              Running live. Attempts appear below as they finish, and the
              report link appears when the job reaches a verdict.
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
            Attempt {attempt.n} ·{" "}
            {attempt.exit_code === null
              ? "no container run (syntax check)"
              : `exit code ${attempt.exit_code}`}
          </h3>
          <LogBlock log={attempt.log} />
        </div>
      ))}
    </>
  );
}
