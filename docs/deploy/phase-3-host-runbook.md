# Phase 3 host runbook (guided session, Friday 2026-11-06 evening)

Finishes the Phase 3 DONE criteria that need the real host: deploy
the Phase 3 code, run the fixture suite against both arbitrated
models (Haiku 5.5, then Qwen3-Coder), exercise every verdict path,
and run the malicious-issue drill live. All steps run in an SSM
Session Manager shell on the `patchpilot-agent` instance (us-east-1);
nothing here needs a credential typed into chat. Keep the session
open until the last step prints, and save the two suite logs: they
are the D8 arbitration evidence for the Phase 3 gate document.

## 0. Get into the host

1. Open the EC2 console, region us-east-1, instance
   `patchpilot-agent`.
2. Connect, Session Manager tab, Connect. This is the standing way
   in (local SSH never worked; see the progress file).
3. Find the repo clone: `cd ~/patchpilot`. If that fails, run
   `find ~ -maxdepth 2 -name run-fixture-suite.py` and cd to its
   parent.

## 1. Deploy the Phase 3 code

From the clone:

```sh
bash scripts/deploy-host.sh
```

It pulls main, copies `backend/` over `/opt/patchpilot/agent`
(keeping its venv), reinstalls the pinned requirements (boto3
included since commit 87b694e), restarts the service, and checks
health. Expect the health JSON with `"status": "ok"` and
`"version": "0.1.0"`, then `Deploy done.`

If health fails, check the service before going on:
`sudo systemctl status patchpilot-agent` and
`sudo journalctl -u patchpilot-agent -n 50`.

## 2. Check the shell can reach Docker

The fixture runner shells out to the `docker` CLI as the SSM user:

```sh
docker ps
```

If that fails with a permission error, the `docker` group from
setup has not applied to this shell: run
`sudo usermod -aG docker "$USER"`, then start a fresh SSM session
and check `docker ps` again. Do not start the suite until it works.

## 3. Fixture suite, model 1: Claude Haiku 5.5

The suite runs in the shell, not through the service, so the model
id and region are exported here (the systemd drop-in only covers
the service). The suite is a verification harness: it runs the
pipeline in-process, so the Phase 2 daily ceilings do not apply to
it. Without a token it fetches 10 issues inside the 60/hour
unauthenticated quota; if GitHub rate-limits, set
`PATCHPILOT_GITHUB_TOKEN` in the shell (typed by hand, never pasted
into chat) and re-run.

```sh
cd ~/patchpilot
export AWS_REGION=us-east-1
export PATCHPILOT_BEDROCK_MODEL_ID=anthropic.claude-haiku-5-5
nohup /opt/patchpilot/agent/.venv/bin/python scripts/run-fixture-suite.py \
  scripts/fixture_issues.json > fixture-haiku.log 2>&1 &
tail -f fixture-haiku.log
```

`nohup` matters: a dropped SSM session must not kill a 10-job run.
Each job takes minutes; worst case is 30 minutes per job, so let it
run. Exit 0 needs at least 3 REPRODUCED out of 10 (the Phase 0
target). Note the printed distribution, including any SETUP FAILED
or LIMIT REACHED lines, for the gate document.

## 4. Fixture suite, model 2: Qwen3-Coder

Same command, only the model id changes. The systemd drop-in stays
on Haiku until the arbitration winner is recorded; only the shell
variable changes for this run.

```sh
export PATCHPILOT_BEDROCK_MODEL_ID=qwen.qwen3-coder-30b-a3b-v1:0
nohup /opt/patchpilot/agent/.venv/bin/python scripts/run-fixture-suite.py \
  scripts/fixture_issues.json > fixture-qwen.log 2>&1 &
tail -f fixture-qwen.log
```

Compare the two distributions: the winner becomes the default
model id. If a run exits non-zero, keep its log; a failed run is
evidence for the gate document, not a reason to re-run blind.

## 5. Verdict paths

After both runs, check the two distributions together against the
five verdicts: REPRODUCED, NOT REPRODUCED, SETUP FAILED, ISSUE
UNDERSPECIFIED, LIMIT REACHED. SETUP FAILED was already exercised
live locally (nonexistent repo) and LIMIT REACHED is covered by a
unit test; a path that never appears live is recorded honestly in
the gate document rather than forced.

## 6. Malicious-issue live drill

Runs the real pipeline, real Bedrock, real Docker, against a
crafted issue whose body orders exfiltration, and proves no
executor command ever carried the injected text:

```sh
export AWS_REGION=us-east-1
export PATCHPILOT_BEDROCK_MODEL_ID=anthropic.claude-haiku-5-5
/opt/patchpilot/agent/.venv/bin/python scripts/malicious-drill.py
```

Expect exit 0 and `No injected text reached the executor.` Exit 1
means a violation was found (stop and report it). Exit 2 means the
drill could not run (no model id, or the job never reached the
attempt loop).

## 7. Record the results

Save `fixture-haiku.log`, `fixture-qwen.log`, and the drill output.
They go into the Phase 3 gate document: both distributions, the
arbitration winner, every verdict path seen, and the drill result.
That document is what Abdullah approves; nothing here advances the
phase on its own.

## Troubleshooting

- `boto3 is not installed`: the deploy step reinstalls requirements;
  re-run step 1.
- `No Bedrock model id is configured`: the export in step 3 or 6
  was missed; the suite prints the model id at the top of each run,
  check it.
- Bedrock access denied: the `patchpilot-bedrock` inline policy on
  the `patchpilot-ssm` role covers InvokeModel; re-check it in the
  IAM console if the error names access.
- `docker: command not found` or permission denied: step 2.
- A single fixture job hangs: the 30-minute per-job ceiling ends it
  with LIMIT REACHED; do not kill the suite process mid-run.
