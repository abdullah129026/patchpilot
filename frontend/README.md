# PatchPilot frontend

Next.js frontend for PatchPilot. Phase 1 scope: design system, layout shell,
landing page, job submission form, live job view, and report page, all working
against fixture data. Real jobs arrive with the Phase 3 runner.

## Develop

```sh
npm install
npm run dev
```

To wire the live agent service (job submission and real job pages), set:

```sh
NEXT_PUBLIC_AGENT_URL=http://localhost:8000 npm run dev
```

Set `NEXT_PUBLIC_SITE_URL` to the deployed frontend URL (in the Vercel
project settings) so the sitemap and Open Graph metadata use the real
domain; until it is set the sitemap stays empty rather than guessing
one.

Without it, the submission form routes to a sample report rather than faking
a job, and the job/report pages serve the three sample jobs from the
fixture suite.

## Build

```sh
npm run build
```

## Design rules

Inter for UI text (next/font), JetBrains Mono for code and logs. No gradients,
no glassmorphism, no emoji icons. Logs and issue text render as text, never
HTML. On the report page, verdict comes first, evidence second, and AI
suggestions are visually distinct from verified facts.
