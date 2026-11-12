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

### 2. Security group SSH rule is 0.0.0.0/0 (Medium)

Open since launch (known since 2026-11-02). Access is via SSM now,
so the SSH rule can be deleted outright. Founder step (console):
EC2 > Security Groups > the patchpilot-agent group > delete the
inbound SSH rule. No replacement is needed.

### 3. No unattended security updates (Low)

setup-host.sh now installs unattended-upgrades and enables it.
Founder step (SSM, live host): install and enable it there too
(`sudo apt install -y unattended-upgrades && sudo systemctl enable
--now unattended-upgrades`). A host firewall (ufw) was considered
and deliberately left out: ufw's default FORWARD policy can break
Docker's container networking, and the security group already
filters inbound (22 from his IP, 80/443 for Caddy). Revisit ufw
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

### 5. Base images pinned by tag only (Medium)

python:3.12-slim, node:22-slim, gcc:13. A tag can move under the
build. Digest pinning is the fix, but the digests could not be
fetched from this VM: the registry-1.docker.io manifest request
kills the session (the egress proxy path to that host is unusable
here), while auth.docker.io answers fine. Fetch on a host with
direct Docker Hub access:

```sh
docker buildx imagetools inspect python:3.12-slim --format '{{json .Manifest}}'
```

or via the registry API (token from auth.docker.io, then the
Docker-Content-Digest header on the manifest request). Record the
three digests in backend/app/config.py as `image@sha256:...` and
re-run the suite; the runner uses the config values as-is. Open.

## Checklist status (Phase 5 DONE bar)

- [x] Dependency audit clean (pip-audit, 2026-11-12)
- [x] Token budget enforced, rate limits distinguished, ceilings
      hardened, prompt excerpt capped, fail-fast LLM, stale-job sweep
- [x] Failure drills: LLM down, GitHub rate-limited, host down,
      takedown — all end in honest user-facing states
- [x] Secrets review: none in code, logs, or the repo
- [ ] Digest pinning (open, method documented above)
- [ ] Service runs as an unprivileged user on the live host
      (code-side done, SSM step outstanding)
- [ ] SSH 0.0.0.0/0 rule deleted (console step outstanding)
- [ ] Unattended upgrades on the live host (SSM step outstanding)
- [ ] Host firewall: deferred deliberately (ufw can break Docker
      networking; the security group is the inbound filter)
