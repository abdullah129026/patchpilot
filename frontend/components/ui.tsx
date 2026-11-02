"use client";

import { useState } from "react";
import { VERDICT_EXPLANATIONS } from "@/lib/fixtures";

export function VerdictBadge({ verdict }: { verdict: string }) {
  return <span className={`verdict ${verdict}`}>{verdict.replaceAll("_", " ")}</span>;
}

export function VerdictExplanation({ verdict }: { verdict: string }) {
  const text = VERDICT_EXPLANATIONS[verdict];
  if (!text) return null;
  return <p>{text}</p>;
}

export function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Clipboard API unavailable (non-secure context): select fallback
      // is intentionally omitted; the text is visible on the page.
      return;
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <button type="button" className="secondary" onClick={copy}>
      {copied ? "Copied" : label}
    </button>
  );
}

// Rendered as text, never HTML: logs and issue text are untrusted data,
// and React escapes them by construction.
export function LogBlock({ log }: { log: string }) {
  return <pre className="log">{log}</pre>;
}

export function CodeBlock({ code }: { code: string }) {
  return <pre className="code">{code}</pre>;
}
