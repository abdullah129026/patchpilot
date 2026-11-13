# Host hardening review — Phase 5 (2026-11-12)

Scope: the EC2 host that runs the agent service (patchpilot-agent,
i-012ac729578d15c80, us-east-1, Ubuntu 24.04, t3.medium), reviewed
from the repo (scripts/setup-host.sh, scripts/deploy-host.sh,
docs/deploy/*.md) and the as-built state recorded 2026-11-11. The
live host was not re-entered in this run; items marked "founder
step" need an SSM session, and the Caddyfile below is a
reconstruction of the Nov 11 setup to be checked against the host
file (`cat /etc/caddy/Caddyfile`) at the next session.

## What is already sound

- The agent service binds 127.0.0.1:8000 only; the internet reaches
  it solely through Caddy. No service port is open to the internet.
- Job containers never get the Docker socket, no privileged flag,
  capabilities dropped, CPU/memory/pids caps, network off at run
  time (verified in backend/app/runner.py).
- Job workspaces are deleted at job end in all paths (pipeline
  finally block); reports are plain JSON on disk.
- No secrets in the repo or the scripts: config comes from the
  environment only, the GitHub token (when set) is read-only and
  lives in the service environment, the delete token is stored only
  as a SHA-256 hash and compared with hmac.compare_digest.
- Kill switch is documented and was tested live on 2026-11-11
  (file pause 503s submissions, systemctl stop takes the service
  down, restart restores it).
- Access is via SSM (patchpilot-ssm role); the original SSH key
  path never worked, so nothing depends on SSH.

## Findings

### 1. The agent service runs as root (High)

The systemd unit in scripts/setup-host.sh has no `User=`, so
uvicorn runs as root. A compromise of the service (the one process
that talks to Docker and the network) is a compromise of the host
user. Fix (code-side, in this run): setup-host.sh now creates a
`patchpilot` system user, adds it to the docker group, chowns
/opt/patchpilot to it, and the unit runs as that user.
Founder step (SSM, live host): the unit file on the host is not
touched by scripts/deploy-host.sh, so apply it by hand:

```sh
sudo useradd --system --no-create-home --shell /usr/sbin/nologin patchpilot
sudo usermod -aG docker patchpilot
sudo chown -R patchpilot:patchpilot /opt/patchpilot
sudo systemctl edit patchpilot-agent   # add under [Service]:
#   User=patchpilot
#   Group=patchpilot
sudo systemctl daemon-reload
sudo systemctl restart patchpilot-agent
curl http://127.0.0.1:8000/health
```

### 2. Security group SSH rule (Medium) — corrected 2026-11-12, not 0.0.0.0/0

The original wording here said the rule was 0.0.0.0/0 since launch.
That premise was wrong: his 2026-11-07 screenshot showed port 22
locked to a single IP (source starting 103.10), never 0.0.0.0/0,
and he deleted the rule anyway that day at 17:55 PKT
(memory/2026-11-07.md, line 19; item marked closed for good).
Access is via SSM, nothing depends on SSH. This finding is closed
and must not be re-raised as a 0.0.0.0/0 issue.

### 3. No unattended security updates (Low)

setup-host.sh now installs unattended-upgrades and enables it.
Founder step (SSM, live host): install and enable it there too
(`sudo apt install -y unattended-upgrades && sudo systemctl enable
--now unattended-upgrades`). A host firewall (ufw) was considered
and deliberately left out: ufw's default FORWARD policy can break
Docker's container networking, and the security group already
filters inbound (80/443 for Caddy; no SSH rule, it was deleted
2026-11-07). Revisit ufw
only with a scratch-instance test, not on the live host.

### 4. The Caddy setup lives only on the host (Medium)

The public endpoint was built 2026-11-11 (A record
agent.fluxyai.codes to 32.199.159.68, security group 80/443,
Caddy 2.11.9 reverse proxy to 127.0.0.1:8000, automatic HTTPS),
but no Caddyfile is in the repo, so a host rebuild loses it.
As-built reconstruction (verify against /etc/caddy/Caddyfile):

```
agent.fluxyai.codes {
    reverse_proxy 127.0.0.1:8000
}
```

Install on a fresh host (now in docs/deploy/ec2-setup.md):

```sh
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

Then write the Caddyfile above to /etc/caddy/Caddyfile and
`sudo systemctl reload caddy`. The Vercel variable
NEXT_PUBLIC_AGENT_URL=https://agent.fluxyai.codes is already set.

### 5. Base images pinned by tag only (Medium) — fixed 2026-11-12

python:3.12-slim, node:22-slim, gcc:13 were pinned by tag only. A
tag can move under the build. Fixed: the digests were fetched on
the EC2 host (docker pull + RepoDigests; buildx is not installed
there) and pinned as image@sha256:... in backend/app/config.py
(commit ac23667):

- python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
- node:22-slim@sha256:e9f565d32859f0cbfb52125eafe8be39390f24dac302dc3cdf566e8ba3ab21ee
- gcc:13@sha256:8c0fe724784c6d617cb582f79ddaf5dd2233aaba2fb7a14e0b9d03348fea8088

Takes effect on the host at the next deploy-host.sh run. The
registry-unreachable-from-this-VM note from the first draft is
moot: the digests came from the host, not from here.

## Checklist status (Phase 5 DONE bar)

- [x] Dependency audit clean (pip-audit, 2026-11-12)
- [x] Token budget enforced, rate limits distinguished, ceilings
      hardened, prompt excerpt capped, fail-fast LLM, stale-job sweep
- [x] Failure drills: LLM down, GitHub rate-limited, host down,
      takedown — all end in honest user-facing states
- [x] Secrets review: none in code, logs, or the repo
- [x] Digest pinning (fixed 2026-11-12, commit ac23667; takes
      effect on the host at the next deploy)
- [ ] Service runs as an unprivileged user on the live host
      (code-side done, SSM step outstanding)
- [ ] SSH rule: corrected 2026-11-12, never 0.0.0.0/0 (single IP 103.10..., deleted 2026-11-07 17:55 PKT); live state not asserted here, console confirmation already requested in the Nov 12 Phase 5 message
- [ ] Unattended upgrades on the live host (SSM step outstanding)
- [ ] Host firewall: deferred deliberately (ufw can break Docker
      networking; the security group is the inbound filter)
