# EC2 host setup (founder console steps)

Decision D1: the agent service runs on a dedicated EC2 host paid from
the AWS Activate credits. Provisioning happens in the founder's own
AWS console. Nothing in this document asks for credentials.

## Launch the instance

1. Open https://console.aws.amazon.com/ec2/ and sign in.
2. Region: US East (N. Virginia), us-east-1.
3. Launch instance, name it `patchpilot-agent`.
4. AMI: Ubuntu Server 24.04 LTS (x86_64).
5. Instance type: t3.medium (4 GiB is the realistic floor; the
   t4g.small free trial at 2 GiB is too tight for installs plus Docker).
6. Key pair: create or pick an existing one, keep the private key safe.
7. Security group: allow SSH (port 22) from your IP only. The
   public agent endpoint (below) also needs ports 80 and 443 open
   to the internet for Caddy. The agent service itself binds
   localhost only and is never exposed directly.
8. Storage: 30 GB gp3 (default is fine).
9. Launch, then reach the instance via SSM Session Manager (the
   standing way in; local SSH never worked reliably) or SSH with
   the key pair.

## Public agent endpoint (as built 2026-11-11)

The service is reachable at https://agent.fluxyai.codes through
Caddy, which terminates TLS and reverse-proxies to the localhost
service. Steps, in order:

1. Cloudflare: A record `agent` on fluxyai.codes pointing to the
   instance's public IP (32.199.159.68), DNS only (no Cloudflare
   proxy), so Caddy can answer the ACME challenge itself.
2. Security group: allow inbound 80 and 443 from anywhere
   (0.0.0.0/0), keeping 22 restricted to your IP.
3. On the host, install Caddy (see docs/deploy/host-hardening-review.md
   for the install commands) and write /etc/caddy/Caddyfile:

   ```
   agent.fluxyai.codes {
       reverse_proxy 127.0.0.1:8000
   }
   ```

   Then `sudo systemctl reload caddy`.
4. Verify from outside: `curl https://agent.fluxyai.codes/health`
   returns `{"status":"ok",...}`.
5. In Vercel (project `patchpilot`, production):
   NEXT_PUBLIC_AGENT_URL=https://agent.fluxyai.codes, then redeploy.
   The frontend only picks the URL up at build time.

## Install the base

```sh
git clone https://github.com/abdullah129026/patchpilot.git
cd patchpilot
bash scripts/setup-host.sh
```

Then copy `backend/` to `/opt/patchpilot/agent`, create its venv,
install `backend/requirements.txt`, and start the service:

```sh
sudo systemctl enable --now patchpilot-agent
curl http://127.0.0.1:8000/health
```

## Rebuild note

If the host ever dies, launch a fresh instance with the steps above
and re-run `scripts/setup-host.sh`. Reports are static artifacts; the
host holds no unique state beyond the current job directories.

## Kill switch

Two levels, both documented in `docs/deploy/kill-switch.md`: pause new
jobs with `sudo touch /opt/patchpilot/jobs/.paused` (service stays up,
submissions get 503), or stop everything with `sudo systemctl stop
patchpilot-agent`.
