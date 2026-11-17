# Post-launch note: what the real verdict distribution looks like

Written 2026-11-17, Phase 6. This is the record Phase 0 section 0.6 asks
for at launch. It gets updated, not rewritten, when the first external job
lands or the host state changes.

## Launch posts

- LinkedIn, Dev.to, Builder Center: fired 2026-11-16 from the main chat,
  with the corrected numbers (lead 7, then the correction to 3), approved
  as written by Abdullah 2026-11-16 15:13 PKT.
  - LinkedIn: https://www.linkedin.com/feed/update/urn:li:activity:7528038021003227136/
  - Dev.to: https://dev.to/muhammad_abdullahshah_96/i-built-a-tool-that-proves-your-bug-before-you-fix-it-and-it-missed-7-out-of-10-3fg
  - Builder Center: https://builder.aws.com/post/3MBVrPzorcOpbQGyhh5WoQ38gFF_p/patchpilot-is-live-3-of-10-on-the-re-run-and-the-misses-are-published-too
- Show HN: not submitted. Hacker News redirected the new account
  (abdullahshaak) to /showlim, temporarily restricting Show HN posts
  from new accounts. Left at his call 2026-11-16; do not retry until
  he raises it.

## The real verdict distribution

Three sources, kept separate, no blending.

1. Fixture benchmark, the measured number. Latest run 2026-11-15,
   Qwen3-Coder-30B via Bedrock, attempt feedback loop live, same 10
   fixtures at the same pinned pre-fix commits: 3 REPRODUCED, 7
   NOT_REPRODUCED, 0 SETUP_FAILED, 0 ERROR. Hits: pyflakes#764,
   humanize#17, humanize#122. First run 2026-11-06 scored 7 of 10;
   that number is history in the case study, not the headline. The
   four flips: pyflakes#834, pyupgrade#194, packaging#638,
   humanize#57. One run against one run, so no causation claim about
   the loop: whether it helped, hurt, or neither is still open.
2. Live jobs through the public endpoint before the host stop: 2 jobs
   total. 4f7d74539a2f (humanize#57, NOT_REPRODUCED, correct: the bug
   is fixed at current upstream HEAD; fixtures reproduce it only
   because they pin the pre-fix base commit) and b60190039918
   (humanize#512, ISSUE_UNDERSPECIFIED drill, an honest underspecified
   state). Zero SETUP_FAILED, zero ERROR live.
3. External jobs from the launch: none yet. Zero submissions from
   outside since the posts went out.

## Why zero external jobs

The host was stopped at his call 2026-11-16 17:53 PKT (EC2
i-012ac729578d15c80, stopped not terminated, about $30 a month burn
with no expected return). agent.fluxyai.codes is down: the public
IPv4 was released, a restart gets a new IP, and DNS would need
updating. The demo accepts no jobs while the host is stopped. The
landing form fails honestly when a visitor submits ("Could not reach
the agent service. Try a sample report below."). The sample reports
and the case study stay live on Vercel.

## Against the Phase 6 DONE bar

- Launch posts: out on 3 of 4 channels (Show HN blocked, his call).
- First external jobs: not run, and cannot run until he restarts the
  host (his call).
- This note: written.

## What is not claimed

- No score above 3 of 10 for the loop version until another
  measurement says otherwise.
- No traffic or reach claim is made here. The posts went out one day
  ago and no external job has been submitted.
- JS and C++ reproduction paths remain unit-tested only; live proof
  is Python only.
- The Haiku head-to-head never ran (AccessDenied on the account), so
  Qwen is the default because it is the only measured model.
