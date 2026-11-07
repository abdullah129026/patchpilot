# Launch posts (DRAFT — for Abdullah's approval, do not post yet)

Hold: the live service still points at the Haiku model id, which the
account cannot call. These posts go out only after the host step in
the progress file is done (switch PATCHPILOT_BEDROCK_MODEL_ID to
qwen.qwen3-coder-30b-a3b-v1:0 and restart the service). All numbers
below are from the real fixture run on 2026-11-06, Qwen3-Coder-30B,
7 of 10 reproduced. Nothing here is a claim the case study does not
already back up.

## LinkedIn

Your issue says it crashes. PatchPilot proves it.

I built a tool that takes a public GitHub issue link, reproduces the
bug in a Docker sandbox, and hands back a reproduction script, a
failing test, and a suggested fix diff, with the logs as proof. The
verdict is computed from exit codes and log matches. The model never
gets to grade its own work.

First measured run, ten real issues from pyflakes, pyupgrade,
packaging, and humanize: 7 reproduced, 3 missed. The misses are on
the case study page too, because a tool that only shows hits cannot
be trusted.

It also survived a malicious issue that ordered it to exfiltrate
data. The only commands that reached the executor were the repro
script and the test run.

Try it, or read the case study first. Link in the comments.

## Dev.to

Title: I built a tool that proves your bug before you fix it, and it
missed 3 out of 10

Body: same story as the LinkedIn post, then the method. Ten curated
Python issues, each checked twice by hand (error at the base commit,
gone at the fix commit). The run reproduces from the issue text
alone. The verdicts are deterministic: exit codes, error-signature
match, test failing before and passing after. Six bugs the live host
runs found that unit tests could not see, one line each. The three
misses, and why the attempt loop retrying the identical prompt six
times is the known weakness. Link to the case study and the sample
reports. Close with the repo link.

## Builder Center

Short post, same numbers, framed for builders: the fixture suite as
the proof, Bedrock on Activate credits as the spend story, the six
host bugs as the lesson (unit tests fake the exact boundary that
failed in production: the model client, the container runtime).
Link to the case study.

## Show HN

Title: Show HN: PatchPilot, reproduces GitHub issues in a sandbox
and returns a failing test

Body: one paragraph on the problem (maintainers cannot reproduce
most reports, so reports stall). One paragraph on the tool: paste an
issue link, get a repro script, a failing test, a suggested fix diff,
logs as proof. Honest numbers up front: 7 of 10 on the first measured
run, misses listed. What it is not: no PRs, no comments, nothing
posted to your repo. Link to the live demo and the case study.
