"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getFixture, issueUrl, type Job } from "@/lib/fixtures";
import { track } from "@/lib/analytics";
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
  const [startError, setStartError] = useState(false);
  const startedRef = useRef(false);

  async function startJob(id: string) {
    const agentUrl = process.env.NEXT_PUBLIC_AGENT_URL;
    if (!agentUrl) return;
    try {
      const res = await fetch(`${agentUrl}/api/jobs/${id}/run`, {
        method: "POST",
      });
      if (res.ok) {
        track("job_started");
        setJob(await res.json());
        setStartError(false);
      } else {
        // The job exists but the start was refused (paused, already
        // running, or the service said no): say so, and offer a retry
        // instead of leaving the job visibly queued forever.
        setStartError(true);
      }
    } catch {
      setStartError(true);
    }
  }

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
        startJob(id);
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
          {job.fixture && " · sample job from the fixture suite"}
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
              <Link href="/jobs/sample-humanize-57">sample-humanize-57</Link>.
              {job.queue_position !== undefined && job.queue_position > 1 && (
                <>
                  {" "}Position {job.queue_position} in the queue.
                </>
              )}
            </p>
          </div>
        )}
        {startError && (
          <div className="notice">
            <p>
              The agent service did not start this job. It may be down or
              paused; the job is still queued and nothing was lost.
            </p>
            <p>
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setStartError(false);
                  startJob(job.id);
                }}
              >
                Try starting it again
              </button>
            </p>
          </div>
        )}
        {job.status === "failed" && job.detail && (
          <div className="notice">
            <p>{job.detail}</p>
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
