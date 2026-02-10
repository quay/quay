# Getting Started with Quay Local Development

This guide walks you through setting up a local Quay development environment from scratch.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Starting the Environment](#starting-the-environment)
- [Stopping the Environment](#stopping-the-environment)
- [Running the React Frontend](#running-the-react-frontend)
- [Using Quay](#using-quay)
- [Applying Code Changes](#applying-code-changes)
- [Troubleshooting](#troubleshooting)
- [Running Tests](#running-tests)
- [Contributing](#contributing)
- [Deploying Quay (Non-Development)](#deploying-quay-non-development)

## Prerequisites

- **Podman** (recommended) or Docker
- **podman-compose** or docker-compose
- **Python 3.12**
- **Node.js 18+**

### Installing Podman on macOS

```bash
brew install podman podman-compose
podman machine init
podman machine start
```

### Configuring Podman Machine Resources

The default Podman machine may not have enough memory to build and run Quay. If you encounter out-of-memory errors (exit code 137) during the build process, you need to allocate more resources.

**Check current resources:**
```bash
podman machine inspect
```

**Increase memory and CPU (recommended: 8GB+ memory, 4+ CPUs):**
```bash
podman machine stop
podman machine set --memory 8192 --cpus 4
podman machine start
```

### Installing Pre-commit Hooks

Run the following in the quay directory to install pre-commit checks (trailing whitespace, EOF newlines, secret leak detection, black formatting):

```bash
make install-pre-commit-hook
```

Or manually:
```bash
pip install pre-commit==4.5.0
pre-commit install
```

## Quick Start

```bash
# Clone the repository
git clone https://github.com/quay/quay.git
cd quay

# Start all services
make local-dev-up

# Access Quay at http://localhost:8080
```

## Starting the Environment

### Basic Setup (Quay + PostgreSQL + Redis)

```bash
make local-dev-up
```

This starts the following services:

| Service | Local Address | Container Name |
|---------|---------------|----------------|
| Quay UI | http://localhost:8080 | quay-quay |
| PostgreSQL | localhost:5432 | quay-db |
| Redis | localhost:6379 | quay-redis |

### With Clair Security Scanner

```bash
make local-dev-up-with-clair
```

Additional services started:

| Service | Local Address | Container Name |
|---------|---------------|----------------|
| Clair | localhost:6000 (from Quay container) | quay-clair |
| Clair Database | localhost:5433 | clair-db |

*Note: Clair runs in the network namespace of the Quay container, allowing Quay to communicate with Clair over localhost.*

## Stopping the Environment

```bash
make local-dev-down
```

## Running the React Frontend

Quay has two frontends:
- **Legacy Angular frontend**: Served automatically by the Quay container
- **New React frontend (PatternFly)**: Requires separate dev server for development

### Starting the React Dev Server

```bash
cd web
npm install
npm run start
```

The React frontend will be available at **http://localhost:9000** and proxies API requests to the Quay backend at http://localhost:8080.

The dev server has hot-reloading enabled - changes to React code in `web/src/` will automatically refresh in the browser.

### Building React Frontend Only

```bash
cd web
npm run build
```

## Using Quay

### Creating Your First Account

1. Visit http://localhost:8080
2. Click "Create Account"
3. Use the username `admin` to create a superuser account

### Pushing Images to Local Quay

```bash
# Login to your local Quay instance
podman login --tls-verify=false localhost:8080

# Tag an existing image
podman tag ubuntu:latest localhost:8080/{org}/{repo}:{tag}

# Push to Quay
podman push --tls-verify=false localhost:8080/{org}/{repo}:{tag}
```

Replace `{org}`, `{repo}`, and `{tag}` with your organization name, repository name, and tag.

## Applying Code Changes

### Backend (Python) Changes

Code is mounted as a volume with hot-reload enabled. Most Python changes take effect automatically. For some changes, restart the Quay container:

```bash
podman restart quay-quay
```

### Legacy Frontend (Angular) Changes

```bash
npm install
npm run watch  # Auto-rebuilds on changes
```

### React Frontend Changes

If running `npm run start` in the `web/` directory, changes are hot-reloaded automatically.

## Troubleshooting

### Out of Memory Errors (Exit Code 137)

If containers crash with exit code 137 during build or runtime, the Podman machine doesn't have enough memory.

**Solution:**
```bash
podman machine stop
podman machine set --memory 8192 --cpus 4
podman machine start
make local-dev-up
```

### Port Conflicts

Ensure nothing else is using ports 8080, 5432, or 6379:
```bash
lsof -i :8080
lsof -i :5432
lsof -i :6379
```

### Firewall Blocking Traffic

Firewalld may block container network traffic. Try temporarily disabling it:
```bash
sudo systemctl stop firewalld
```

### Container Not Reflecting Code Changes

1. Verify volume mounts are correct in `docker-compose.yaml`
2. Restart the container:
   ```bash
   podman restart quay-quay
   ```

### Database Connection Errors

Restart the database, then Quay:
```bash
podman restart quay-db
podman restart quay-quay
```

### Viewing Logs

```bash
# View Quay logs
podman logs quay-quay

# Follow logs in real-time
podman logs -f quay-quay

# View all container logs
podman-compose logs -f
```

### Shell Access

```bash
# Shell into Quay container
podman exec -it quay-quay bash

# Database shell
podman exec -it quay-db psql -U quay -d quay
```

### Rebuilding Containers

```bash
# Rebuild all containers
make local-docker-rebuild

# Include Clair in rebuild
CLAIR=true make local-docker-rebuild
```

## Running Tests

```bash
# Run a single test file
TEST=true PYTHONPATH="." pytest path/to/test.py -v

# Run a specific test
TEST=true PYTHONPATH="." pytest path/to/test.py::TestClass::test_fn -v

# Run all unit tests
make unit-test

# Run registry protocol tests
make registry-test

# Type checking
make types-test
```

See [TESTING.md](/TESTING.md) for detailed testing information.

## Contributing

Before contributing, please read our [contributing guidelines](../.github/CONTRIBUTING.md).

## Deploying Quay (Non-Development)

If you're looking to deploy Quay for production use (not development), see:

- [Deploy a Proof-of-Concept](https://docs.projectquay.io/deploy_quay.html)
- [Deploy to OpenShift with the Quay Operator](https://docs.projectquay.io/deploy_quay_on_openshift_op_tng.html)
- [Deploy with High Availability](https://docs.projectquay.io/deploy_quay_ha.html)
