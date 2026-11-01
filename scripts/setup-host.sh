#!/usr/bin/env bash
# Rebuild the PatchPilot Docker host from a fresh Ubuntu 24.04 instance.
# Run on the instance itself, after it is launched from the AWS console
# (see docs/deploy/ec2-setup.md). No secrets are read or written here:
# the agent service takes its configuration from environment only, and
# the GitHub token used for issue fetching is read-only and lives in
# the service environment, never in this script.
set -euo pipefail

sudo apt-get update -y
sudo apt-get install -y docker.io python3 python3-venv python3-pip
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER" || true

sudo mkdir -p /opt/patchpilot /opt/patchpilot/jobs
sudo chown "$USER:$USER" /opt/patchpilot /opt/patchpilot/jobs

cat <<'UNIT' | sudo tee /etc/systemd/system/patchpilot-agent.service > /dev/null
[Unit]
Description=PatchPilot agent service
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/patchpilot/agent
Environment=PATCHPILOT_JOB_DIR=/opt/patchpilot/jobs
ExecStart=/opt/patchpilot/agent/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
UNIT

echo "Host base ready. Next: copy backend/ to /opt/patchpilot/agent,"
echo "create its venv, then: sudo systemctl enable --now patchpilot-agent"
echo "Note: the service binds localhost only. Public exposure, if any,"
echo "arrives behind a reverse proxy in a later phase, never by opening"
echo "the service port to the internet."
