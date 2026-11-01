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
7. Security group: allow SSH (port 22) from your IP only. Allow no
   other inbound ports. The agent service binds localhost only.
8. Storage: 30 GB gp3 (default is fine).
9. Launch, then SSH in with the key pair.

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

To stop all job processing immediately: `sudo systemctl stop
patchpilot-agent`. That is the documented abuse kill switch until
Phase 2 adds the ceiling controls.
