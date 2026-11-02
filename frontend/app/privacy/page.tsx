export default function Privacy() {
  return (
    <>
      <h1 style={{ marginTop: 40 }}>Privacy Note</h1>
      <p className="small">Draft for the Phase 4 human copy pass.</p>
      <ul className="tight">
        <li>PatchPilot collects no accounts and no billing information in v1. Jobs live behind shareable links.</li>
        <li>A submitted issue URL, the fetched public issue text, and the job run logs are stored as the job report so the result can be shared and checked.</li>
        <li>Job workspaces (cloned code, containers) are deleted after each job.</li>
        <li>Reports are kept indefinitely as the product public proof, and removed on request (the takedown path lands in Phase 2).</li>
        <li>No secrets are stored in code, logs, or reports. Any API keys live in the host environment only.</li>
      </ul>
    </>
  );
}
