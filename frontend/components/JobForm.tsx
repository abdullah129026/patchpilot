"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { track } from "@/lib/analytics";

const ISSUE_URL =
  /^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/issues\/\d+\/?$/;

export default function JobForm() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [limits, setLimits] = useState<{
    daily_used: number;
    daily_ceiling: number;
    paused?: boolean;
  } | null>(null);

  useEffect(() => {
    const agentUrl = process.env.NEXT_PUBLIC_AGENT_URL;
    if (!agentUrl) return;
    fetch(`${agentUrl}/api/limits`)
      .then((res) => (res.ok ? res.json() : null))
      .then(setLimits)
      .catch(() => null);
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = url.trim();
    if (!ISSUE_URL.test(trimmed)) {
      setError(
        "That does not look like a public GitHub issue URL. Expected: https://github.com/owner/repo/issues/123"
      );
      return;
    }
    setError("");
    const agentUrl = process.env.NEXT_PUBLIC_AGENT_URL;
    if (!agentUrl) {
      // No agent service wired in this build: the honest demo path is a
      // sample report, not a fake job.
      router.push("/report/sample-humanize-57");
      return;
    }
    setBusy(true);
    try {
      const res = await fetch(`${agentUrl}/api/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ issue_url: trimmed }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        setError(detail?.detail ?? "The job could not be submitted.");
        setBusy(false);
        return;
      }
      const job = await res.json();
      track("job_submitted");
      if (job.delete_token) {
        try {
          sessionStorage.setItem(`patchpilot-delete-${job.id}`, job.delete_token);
        } catch {
          // Storage unavailable; the report can still be removed by request.
        }
      }
      router.push(`/jobs/${job.id}`);
    } catch {
      setError("Could not reach the agent service. Try a sample report below.");
      setBusy(false);
    }
  }

  return (
    <>
    {limits?.paused && (
      <div className="notice">
        <p>
          PatchPilot is paused right now. No new jobs are accepted until the
          demo resumes. The sample reports below still work.
        </p>
      </div>
    )}
    <form className="job-form" onSubmit={submit}>
      <input
        type="text"
        value={url}
        onChange={(event) => setUrl(event.target.value)}
        placeholder="https://github.com/owner/repo/issues/123"
        aria-label="Public GitHub issue URL"
        disabled={limits?.paused}
      />
      <button type="submit" className="primary" disabled={busy || limits?.paused}>
        {busy ? "Submitting…" : "Reproduce it"}
      </button>
      {error && <p className="error">{error}</p>}
    </form>
    {limits && (
      <p className="form-note">
        Daily jobs used: {limits.daily_used} of {limits.daily_ceiling}. One
        job runs at a time; extra submissions wait in the queue.
      </p>
    )}
    </>
  );
}
