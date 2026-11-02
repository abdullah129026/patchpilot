export default function AcceptableUse() {
  return (
    <>
      <h1 style={{ marginTop: 40 }}>Acceptable Use</h1>
      <p className="small">Draft for the Phase 4 human copy pass.</p>
      <p>Do not use PatchPilot to:</p>
      <ul className="tight">
        <li>Run malware, miners, or attack tooling through the sandbox.</li>
        <li>Attack third parties, probe other systems, or exfiltrate data.</li>
        <li>Submit repositories or issues for harassment, or to reproduce exploits against systems you do not own.</li>
        <li>Evade the job ceilings (attempts, wall time, per-IP and daily caps).</li>
      </ul>
      <p>Jobs that violate this policy are refused or deleted, and abusive sources are blocked. The abuse and copyright contact is published before launch (Phase 4 launch checklist).</p>
    </>
  );
}
