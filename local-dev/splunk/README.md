# Splunk Local Development Setup

Local Splunk Enterprise instance for testing Quay's audit log integration.

## Quick Start

```bash
# 1. Start Quay stack (if not already running)
make local-dev-up

# 2. Enable Splunk (starts container, creates index/token, merges config)
make enable-splunk

# 3. Restart Quay to apply
docker compose restart quay    # or: podman restart quay-quay
```

## Connection Details

| Setting | Value |
|---------|-------|
| Splunk Web UI | http://localhost:8000 |
| Management API | https://localhost:8089 |
| Username | admin |
| Password | changeme1 |
| Index | quay_logs |

## Verifying Logs

1. Perform actions in Quay UI (http://localhost:8080) - create repos, push images, etc.
2. Open Splunk Web UI (http://localhost:8000), log in with admin/changeme1
3. Go to Search & Reporting
4. Search: `index=quay_logs | head 20`

## Reverting to Database Logging

```bash
cp local-dev/stack/config.yaml.backup local-dev/stack/config.yaml
docker compose restart quay    # or: podman restart quay-quay
```

## Troubleshooting

**Splunk takes a long time to start:** First startup takes ~60-90 seconds. Check health with:
```bash
docker inspect --format='{{.State.Health.Status}}' quay-splunk
```

**Connection errors from Quay:** Ensure Splunk is healthy and on the same Docker network. Check:
```bash
podman logs quay-quay 2>&1 | grep -i splunk
```

**Regenerate tokens:** Re-run the init script:
```bash
docker exec quay-splunk bash /tmp/init-splunk.sh
```
