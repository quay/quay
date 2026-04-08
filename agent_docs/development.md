# Local Development Setup

## Prerequisites

- Docker or Podman
- docker-compose
- Python 3.12
- Node 16+

## Starting the Environment

```bash
# Basic (Quay + PostgreSQL + Redis)
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

## Applying Code Changes

Code is mounted as a volume with hot-reload. For some changes:

```bash
podman restart quay-quay
```

## Volume Mounts

Ensure `docker-compose.yaml` has source code mounted:

```yaml
volumes:
  - ".:/quay-registry"
  - "./local-dev/stack:/quay-registry/conf/stack"
```

Without the mount, code changes won't be reflected.

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

## Frontend Development

### Legacy Angular
```bash
npm install
npm run watch  # Auto-rebuilds on changes
```

### React (in web/)
```bash
cd web
npm install
npm start      # Dev server on :9000
```

## Pre-commit Hooks

```bash
make install-pre-commit-hook
```

## Common Issues

**Port conflicts:** Ensure nothing else uses 8080, 5432, 6379

**Firewall:** May need to allow container traffic

**Code not updating:** Check volume mounts, restart container

**Database errors:** Try `podman restart quay-db` then `podman restart quay-quay`
