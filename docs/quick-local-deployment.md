# Quick Local Deployment

> **For local development**, see [Getting Started](./getting-started.md) which uses `make local-dev-up` for a streamlined experience.

This document describes manual deployment steps for understanding Quay's components or for non-development testing/evaluation purposes.

## Quick Start (Recommended)

For most users, the simplest way to run Quay locally:

```bash
git clone https://github.com/quay/quay.git
cd quay
make local-dev-up
```

Access Quay at http://localhost:8080

To stop:
```bash
make local-dev-down
```

---

## Manual Deployment (Advanced)

The following sections describe how to manually set up each component. This is useful for understanding how Quay works or for custom deployment scenarios.

### Prerequisites

- Podman or Docker
- A directory for Quay data (referred to as `$QUAY` below)

### Optional: Add 'quay' to /etc/hosts

```
127.0.0.1   quay
```

### Set Up PostgreSQL

```bash
mkdir -p $QUAY/postgres
setfacl -m u:26:-wx $QUAY/postgres
podman run -d --rm --name postgresql \
    -e POSTGRES_USER=user \
    -e POSTGRES_PASSWORD=pass \
    -e POSTGRES_DB=quay \
    -p 5432:5432 \
    -v $QUAY/postgres:/var/lib/postgresql/data:Z \
    postgres:15

# Install required extension
podman exec -it postgresql /bin/bash -c 'echo "CREATE EXTENSION IF NOT EXISTS pg_trgm" | psql -d quay -U user'
```

### Set Up Redis

```bash
podman run -d --rm --name redis \
    -p 6379:6379 \
    redis:latest \
    --requirepass strongpassword
```

### Run Quay

```bash
mkdir -p $QUAY/config $QUAY/storage
setfacl -m u:1001:-wx $QUAY/storage

podman run --rm -p 8080:8080 \
    --name=quay \
    --privileged=true \
    -v $QUAY/config:/conf/stack:Z \
    -v $QUAY/storage:/datastorage:Z \
    -d quay.io/projectquay/quay:latest
```

### Test Quay

```bash
podman login --tls-verify=false localhost:8080
podman pull busybox
podman tag busybox:latest localhost:8080/myorg/myrepo:latest
podman push --tls-verify=false localhost:8080/myorg/myrepo:latest
```

## Next Steps

- [Getting Started Guide](./getting-started.md) - Full development setup
- [Quay HA Docs](https://docs.projectquay.io/deploy_quay_ha.html) - Production deployment
- [Quay on OpenShift](https://docs.projectquay.io/deploy_quay_on_openshift.html) - Kubernetes deployment
