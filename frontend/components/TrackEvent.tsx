"use client";

import { useEffect, useRef } from "react";
import { track, type AnalyticsEvent } from "@/lib/analytics";

// Fires one analytics event when the component mounts. Used for
// page-level events (landing_view) in server-rendered pages.
export default function TrackEvent({
  event,
  verdict,
}: {
  event: AnalyticsEvent;
  verdict?: string;
}) {
  const fired = useRef(false);
  useEffect(() => {
    if (fired.current) return;
    fired.current = true;
    track(event, verdict);
  }, [event, verdict]);
  return null;
}
