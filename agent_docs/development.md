# Local Development Setup

For comprehensive onboarding documentation, see [docs/getting-started.md](/docs/getting-started.md).

## Prerequisites

- Podman (recommended) or Docker
- podman-compose or docker-compose
- Python 3.12
- Node.js 18+

## Quick Start

```bash
# Start all services (Quay + PostgreSQL + Redis)
make local-dev-up

# With Clair security scanner
make local-dev-up-with-clair

# Shutdown
make local-dev-down
```

## Services

| Service | Local Address | Container Name |
|---------|---------------|----------------|
| Quay UI | http://localhost:8080 | quay-quay |
| PostgreSQL | localhost:5432 | quay-db |
| Redis | localhost:6379 | quay-redis |
| Clair | localhost:6000 (internal) | quay-clair |

## Podman Machine Resources

If you encounter out-of-memory errors (exit code 137):

```bash
podman machine stop
podman machine set --memory 8192 --cpus 4
podman machine start
```

## Applying Code Changes

Backend code is mounted with hot-reload. For some changes:

```bash
podman restart quay-quay
```

## Frontend Development

### Legacy Angular (static/js/)
```bash
npm install
npm run watch  # Auto-rebuilds on changes
```

### React Frontend (web/)
```bash
cd web
npm install
npm run start  # Dev server on http://localhost:9000
```

The React dev server proxies API requests to the Quay backend at localhost:8080.

## Configuration

Edit `local-dev/stack/config.yaml` for local configuration:

```yaml
SUPER_USERS:
  - admin
FEATURE_SECURITY_SCANNER: true
DB_URI: postgresql://quay:quay@quay-db/quay
```

## Default Accounts

Create a user with username `admin` for superuser access.

## Pushing Test Images

```bash
podman login localhost:8080 -u admin -p password --tls-verify=false
podman tag hello-world localhost:8080/admin/testimage:latest
podman push localhost:8080/admin/testimage:latest --tls-verify=false
```

## Debugging

```bash
# View logs
podman logs quay-quay
podman logs quay-quay -f  # Follow

# Shell into container
podman exec -it quay-quay bash

# Database shell
podman exec -it quay-db psql -U quay -d quay
```

## Rebuild Containers

```bash
# Rebuild all
make local-docker-rebuild

# Include Clair
CLAIR=true make local-docker-rebuild
```

## Pre-commit Hooks

```bash
make install-pre-commit-hook
```

## Common Issues

**Out of memory (exit 137):** Increase Podman machine memory (see above)

**Port conflicts:** Ensure nothing else uses 8080, 5432, 6379

**Firewall:** May need to allow container traffic

**Code not updating:** Check volume mounts, restart container

**Database errors:** Try `podman restart quay-db` then `podman restart quay-quay`
