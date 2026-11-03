"use client";

import { useEffect, useState } from "react";

// Phase 2 removal surface. The submitter holds a delete token issued at
// creation and kept in this browser only; anyone else files a takedown
// request, which is recorded for the project owner instead of deleting
// on an anonymous say-so. Sample reports are synthetic and not removable.
export default function Takedown({
  jobId,
  fixture,
}: {
  jobId: string;
  fixture?: boolean;
}) {
  const [token, setToken] = useState<string | null>(null);
  const [contact, setContact] = useState("");
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [deleted, setDeleted] = useState(false);

  useEffect(() => {
    try {
      setToken(sessionStorage.getItem(`patchpilot-delete-${jobId}`));
    } catch {
      setToken(null);
    }
  }, [jobId]);

  if (fixture) return null;

  const agentUrl = process.env.NEXT_PUBLIC_AGENT_URL;

  async function remove() {
    if (!agentUrl || !token) return;
    if (!window.confirm("Delete this report permanently? This cannot be undone.")) return;
    const res = await fetch(`${agentUrl}/api/jobs/${jobId}`, {
      method: "DELETE",
      headers: { "X-Delete-Token": token },
    });
    if (res.status === 204) {
      try {
        sessionStorage.removeItem(`patchpilot-delete-${jobId}`);
      } catch {
        // Storage unavailable; the report is still deleted server-side.
      }
      setDeleted(true);
    } else {
      setMessage("Could not delete this report. The delete token may have expired.");
    }
  }

  async function requestRemoval(event: React.FormEvent) {
    event.preventDefault();
    if (!agentUrl) return;
    setMessage("");
    const res = await fetch(`${agentUrl}/api/jobs/${jobId}/takedown-request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contact: contact.trim(), reason: reason.trim() }),
    });
    if (res.ok) {
      setMessage("Takedown request recorded. The report stays up until its owner reviews it.");
      setReason("");
    } else {
      setMessage("Could not record the request. Try again later.");
    }
  }

  if (deleted) {
    return (
      <div className="panel" style={{ marginTop: 32 }}>
        <h3>Report deleted</h3>
        <p>This report has been removed.</p>
      </div>
    );
  }

  return (
    <section className="panel" style={{ marginTop: 32 }}>
      <h3>Remove this report</h3>
      {token ? (
        <p>
          You submitted this job from this browser, so you can delete its
          report right now.{" "}
          <button type="button" className="secondary" onClick={remove}>
            Delete this report
          </button>
        </p>
      ) : (
        <p>
          Only the submitter can delete a report directly. If this report
          concerns your repository and should come down, file a request
          and the project owner will review it.
        </p>
      )}
      {!agentUrl && (
        <p className="small">
          The agent service is not wired into this build, so removal cannot
          be completed from here.
        </p>
      )}
      {agentUrl && (
        <form className="stack-form" onSubmit={requestRemoval}>
          <input
            type="text"
            value={contact}
            onChange={(event) => setContact(event.target.value)}
            placeholder="Contact (optional): name or email"
            aria-label="Contact for the takedown request"
          />
          <textarea
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Why should this report come down?"
            aria-label="Reason for the takedown request"
            required
            rows={3}
          />
          <button type="submit" className="secondary">
            Request removal
          </button>
        </form>
      )}
      {message && <p style={{ marginTop: 12 }}>{message}</p>}
    </section>
  );
}
