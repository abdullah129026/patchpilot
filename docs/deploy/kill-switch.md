# Kill switch

Two levels, both are the founder's step in an SSM session on the EC2
host. Nothing here needs a code deploy: the pause check is already in
the service, and the service stop is systemd.

## Level 1: pause new jobs (service stays up)

Refuses new submissions with 503 and refuses to start queued jobs.
Reports and the landing page stay up; the limits endpoint reports
`"paused": true` and the frontend shows a paused notice.

```sh
sudo touch /opt/patchpilot/jobs/.paused
```

Verify from the host:

```sh
curl -s http://127.0.0.1:8000/api/limits | grep paused
# expect: "paused": true
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"issue_url": "https://github.com/a/b/issues/9"}'
# expect: 503
```

Resume:

```sh
sudo rm /opt/patchpilot/jobs/.paused
```

No restart is needed either way: the service checks the file on
every submission and every job start. A job already running when the
file appears finishes; nothing new starts.

## Level 2: stop the service entirely

Use this when pausing submissions is not enough, for example a
running job misbehaving or the host itself needing to go quiet.

```sh
sudo systemctl stop patchpilot-agent
```

Verify:

```sh
sudo systemctl status patchpilot-agent
curl -s http://127.0.0.1:8000/health || echo "service down"
```

Resume:

```sh
sudo systemctl start patchpilot-agent
curl -s http://127.0.0.1:8000/health
# expect: {"status":"ok","service":"patchpilot-agent","version":"0.1.0"}
```

## Why there is no API endpoint for this

v1 has no accounts, so a public pause endpoint would let anyone shut
the demo off. Pausing is a file on the host, reachable only through
SSM, which is the same access that deploys the service.
