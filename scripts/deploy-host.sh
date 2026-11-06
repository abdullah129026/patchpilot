#!/usr/bin/env bash
# Deploy the checked-in backend to the EC2 host's agent service.
# Run on the host itself, from the repo clone (see
# docs/deploy/phase-3-host-runbook.md). Pulls main, copies backend/
# over the service directory while keeping its venv, reinstalls the
# pinned requirements (boto3 included), restarts the service and
# checks health. No secrets are read or written here.
set -euo pipefail

AGENT_DIR="${PATCHPILOT_AGENT_DIR:-/opt/patchpilot/agent}"
VENV="$AGENT_DIR/.venv"
SUDO="${PATCHPILOT_DEPLOY_SUDO-sudo}"
SKIP_SERVICE="${PATCHPILOT_DEPLOY_SKIP_SERVICE:-}"

git pull --ff-only

# Fresh copy of everything the service runs, minus the venv it keeps.
$SUDO rm -rf "$AGENT_DIR/app" "$AGENT_DIR/tests" \
    "$AGENT_DIR/requirements.txt" "$AGENT_DIR/pyproject.toml"
$SUDO cp -r backend/. "$AGENT_DIR/"
if [ ! -x "$VENV/bin/python" ]; then
    $SUDO python3 -m venv "$VENV"
fi
$SUDO "$VENV/bin/pip" install -q -r "$AGENT_DIR/requirements.txt"

if [ -z "$SKIP_SERVICE" ]; then
    $SUDO systemctl restart patchpilot-agent
    sleep 2
    curl -fsS "http://127.0.0.1:8000/health?cb=$(date +%s)"
    echo
fi
echo "Deploy done."
