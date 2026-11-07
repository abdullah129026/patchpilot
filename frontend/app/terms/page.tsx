export default function Terms() {
  return (
    <>
      <h1 style={{ marginTop: 40 }}>Terms of Service</h1>
      <p>PatchPilot is a free demonstration tool. You paste a public GitHub issue URL; PatchPilot attempts to reproduce the reported bug in a sandbox and shows you what it found.</p>
      <ul className="tight">
        <li>You are responsible for the repository you point at. Do not submit issues for repositories you have no legitimate reason to examine.</li>
        <li>Output is machine-generated. A suggested fix diff is a suggestion, not a verified correction, unless its report says the fix was verified by a test transition inside the sandbox.</li>
        <li>Reports disclose that an AI agent produced them and separate what was verified from what was suggested.</li>
        <li>PatchPilot claims no ownership of any fix diff and no endorsement from any upstream project.</li>
        <li>Reports show the source repository license and attribution. If a diff is applied and shared, it takes the source repository license terms.</li>
        <li>Jobs may be refused or deleted at any time, and the service may be stopped without notice.</li>
        <li>Job workspaces are deleted after each job. Reports are kept (see the privacy note) and removed on request.</li>
      </ul>
    </>
  );
}
