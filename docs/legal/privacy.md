# Privacy Note (DRAFT)

Status: draft for the Phase 4 human copy pass.

- PatchPilot collects no accounts and no billing information in v1.
  Jobs live behind shareable links.
- A submitted issue URL, the fetched public issue text, and the job's
  run logs are stored as the job's report so the result can be shared
  and checked.
- Job workspaces (cloned code, containers) are deleted after each job.
- Reports are kept indefinitely as the product's public proof, and
  removed on request (the takedown path lands in Phase 2).
- No secrets are stored in code, logs, or reports. Any API keys live
  in the host environment only.
