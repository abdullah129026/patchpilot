// First-party analytics (Phase 4, Phase 0 section 0.5). One POST per
// event to the agent service; nothing is sent when no agent URL is
// configured, and a failed send is silently dropped, never shown to
// the visitor. No cookies, no third party, no personal data.

export type AnalyticsEvent =
  | "landing_view"
  | "job_submitted"
  | "job_started"
  | "verdict_shown"
  | "report_copied_script"
  | "report_copied_test"
  | "diff_expanded"
  | "sample_report_opened";

export function track(event: AnalyticsEvent, verdict?: string) {
  const agentUrl = process.env.NEXT_PUBLIC_AGENT_URL;
  if (!agentUrl) return;
  fetch(`${agentUrl}/api/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event, verdict: verdict ?? null }),
    keepalive: true,
  }).catch(() => {
    // Analytics must never break the page.
  });
}
