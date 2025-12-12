# Implementation Plan: PROJQUAY-9897

## Task Summary

Create CLAUDE.md, AGENTS.md, and GEMINI.md for Quay repositories following progressive disclosure principles.

**Repositories to cover:**
| Repository | Status |
|------------|--------|
| quay/quay | **COMPLETED** |
| quay/quay-operator | Pending (separate PR) |
| quay/container-security-operator | Pending (separate PR) |
| quay/quay-bridge-operator | Pending (separate PR) |
| quay/mirror-registry | Pending (separate PR) |

## Progressive Disclosure Pattern

Based on the reference implementation (yearofbingo) and best practices from humanlayer.dev:

```
CLAUDE.md          → Points to @AGENTS.md (minimal, <60 lines ideal)
AGENTS.md          → Main context document with documentation map
GEMINI.md          → Points to @./AGENTS.md
.claude/docs/*.md  → Detailed topic-specific documentation (progressive disclosure)
```

### Key Principles
1. **Keep CLAUDE.md minimal** - It goes into every session, so only universally applicable info
2. **AGENTS.md as the hub** - Contains project overview and documentation map with pointers
3. **Progressive disclosure** - Detailed docs in `.claude/docs/` loaded on-demand based on task keywords
4. **Cross-agent compatibility** - GEMINI.md references AGENTS.md for shared context

---

## Part 1: quay/quay Repository

### Current State
- `web/AGENTS.md` already exists (comprehensive frontend guide)
- No root CLAUDE.md, AGENTS.md, or GEMINI.md
- Rich codebase with Python backend, React frontend, workers, config-tool

### Files to Create

#### 1. `CLAUDE.md` (root)
Minimal pointer file (~10 lines):
```markdown
@AGENTS.md
```

#### 2. `AGENTS.md` (root)
Main context document (~60-80 lines) containing:
- Project overview (what Quay is)
- Tech stack summary
- Core development commands
- Documentation map pointing to `.claude/docs/` files

#### 3. `GEMINI.md` (root)
```markdown
# GEMINI

Please follow instructions from @./AGENTS.md
```

#### 4. `.claude/docs/` Progressive Disclosure Files

| File | Trigger Keywords | Content |
|------|------------------|---------|
| `backend.md` | API, endpoint, Flask, routes, auth | Backend architecture, endpoints/, data/, auth/ |
| `frontend.md` | UI, React, component, PatternFly | Points to `web/AGENTS.md`, additional context |
| `database.md` | database, migration, schema, model, ORM | Data models, migrations, Alembic |
| `workers.md` | worker, background, job, queue | Workers architecture, common patterns |
| `testing.md` | test, pytest, cypress, coverage | Testing strategy, commands, patterns |
| `config.md` | config, configuration, settings | config.py, config-tool, environment |
| `deployment.md` | deploy, kubernetes, operator, container | Deployment patterns, Dockerfile, compose |

### AGENTS.md Structure for quay/quay

```markdown
# Quay - Developer Agent Context

## Project Overview
Quay is a container registry that builds, stores, and distributes container images.
**Domain**: quay.io

## Tech Stack
- **Backend**: Python 3.11+, Flask, Gunicorn, SQLAlchemy, Alembic
- **Frontend**: React 18, TypeScript, PatternFly 5, React Query
- **Database**: PostgreSQL, Redis (caching)
- **Storage**: S3, GCS, Swift, Ceph, local filesystem

## Core Workflow
- **Start Dev**: `docker-compose up` or local setup via docs/getting-started.md
- **Test Backend**: `pytest` (unit), `pytest --integration` (integration)
- **Test Frontend**: `npm test` (unit), `npm run test:integration` (Cypress)
- **Lint**: `make lint` or `pre-commit run --all-files`

## Documentation Map & Constraints

Read specific documentation if your task involves these keywords:

- **API, Endpoints, Routes, Flask** → `read_file .claude/docs/backend.md`
- **UI, React, Component, PatternFly** → `read_file web/AGENTS.md`
- **Database, Schema, Migration, Model** → `read_file .claude/docs/database.md`
- **Worker, Background Job, Queue** → `read_file .claude/docs/workers.md`
- **Test, Pytest, Cypress** → `read_file .claude/docs/testing.md`
- **Config, Settings, Environment** → `read_file .claude/docs/config.md`
- **Deploy, Kubernetes, Container** → `read_file .claude/docs/deployment.md`

## Universal Conventions
- Follow existing code style (Python: PEP8, TypeScript: ESLint/Prettier)
- Never commit secrets or credentials
- Use descriptive commit messages with JIRA ticket prefix (e.g., PROJQUAY-XXXX)
```

---

## Part 2: Other Repositories

Each operator/tool repo follows the same pattern but with repo-specific content.

### quay/quay-operator
- **Language**: Go
- **Type**: Kubernetes Operator (Operator SDK)
- **Key dirs**: `apis/`, `controllers/`, `pkg/`, `bundle/`, `e2e/`
- **Commands**: `make build`, `make test`, `make deploy`

### quay/container-security-operator (CSO)
- **Language**: Go
- **Type**: Kubernetes Operator for vulnerability scanning
- **Key dirs**: `apis/`, `cmd/`, `labeller/`, `secscan/`, `k8sutils/`
- **Commands**: `make build`, `make test`

### quay/quay-bridge-operator (QBO)
- **Language**: Go
- **Type**: Kubernetes Operator for OpenShift integration
- **Key dirs**: `api/`, `controllers/`, `pkg/`, `bundle/`
- **Commands**: `make build`, `make test`, `make deploy`

### quay/mirror-registry
- **Language**: Go + Ansible
- **Type**: CLI tool for air-gapped Quay deployment
- **Key dirs**: `cmd/`, `ansible-runner/`, `test/`
- **Commands**: `make build`, `make test`

---

## Implementation Steps

### Phase 1: quay/quay (This PR)
1. Create `CLAUDE.md` at root
2. Create `AGENTS.md` at root with documentation map
3. Create `GEMINI.md` at root
4. Create `.claude/docs/` directory with progressive disclosure docs:
   - `backend.md`
   - `database.md`
   - `workers.md`
   - `testing.md`
   - `config.md`
   - `deployment.md`
5. Update existing `web/AGENTS.md` if needed to align with pattern

### Phase 2: Other Repos (Separate PRs)
For each repo (quay-operator, CSO, QBO, mirror-registry):
1. Create `CLAUDE.md` pointing to AGENTS.md
2. Create `AGENTS.md` with repo-specific context
3. Create `GEMINI.md` pointing to AGENTS.md
4. Create `.claude/docs/` if repo is complex enough to warrant it

---

## File Sizes Target

Following the "less is more" principle:
- `CLAUDE.md`: <15 lines (pointer only)
- `AGENTS.md`: 60-100 lines (main context)
- `GEMINI.md`: <10 lines (pointer only)
- `.claude/docs/*.md`: 50-150 lines each (detailed but focused)

---

## Verification

After implementation:
1. Test with Claude Code on various task types
2. Verify progressive disclosure works (docs loaded on keyword match)
3. Ensure no duplicate information between files
4. Validate that the documentation map is accurate

---

## Completed: quay/quay Files

The following files have been created:

```
CLAUDE.md                    # @AGENTS.md pointer
AGENTS.md                    # Main context (~70 lines)
GEMINI.md                    # @./AGENTS.md pointer
.claude/docs/backend.md      # API/endpoint documentation
.claude/docs/database.md     # Database/model documentation
.claude/docs/workers.md      # Background workers documentation
.claude/docs/testing.md      # Testing guide
.claude/docs/config.md       # Configuration guide
.claude/docs/frontend.md     # Frontend overview + pointer to web/AGENTS.md
config-tool/AGENTS.md        # Go-based config validator documentation
```

Existing files preserved:
- `web/AGENTS.md` - Comprehensive frontend guide (already existed)

---

## Templates for Other Repositories

### quay/quay-operator

**CLAUDE.md:**
```markdown
@AGENTS.md
```

**AGENTS.md:**
```markdown
# Quay Operator - Developer Agent Context

## Project Overview

Kubernetes Operator for deploying and managing Quay container registry on OpenShift/Kubernetes.
**Docs**: https://github.com/quay/quay-operator

## Tech Stack

- **Language**: Go 1.21+
- **Framework**: Operator SDK / controller-runtime
- **CRDs**: QuayRegistry, QuayEcosystem (deprecated)
- **Build**: Make, Kustomize, OLM Bundle

## Core Workflow

```bash
# Build
make build                    # Build operator binary
make docker-build            # Build container image

# Test
make test                    # Unit tests
make e2e                     # E2E tests (requires cluster)

# Deploy
make deploy                  # Deploy to current cluster
make undeploy                # Remove from cluster

# Generate
make generate                # Update generated code
make manifests               # Update CRD manifests
```

## Directory Structure

```
apis/quay/v1/        # CRD type definitions (QuayRegistry)
controllers/         # Reconciliation logic
pkg/                 # Business logic packages
  ├── kube/          # Kubernetes client utilities
  └── configure/     # Quay configuration generation
bundle/              # OLM bundle for OperatorHub
config/              # Kustomize manifests
e2e/                 # E2E test suites
```

## Key Concepts

- **QuayRegistry CR**: Main custom resource defining a Quay deployment
- **Components**: Modular features (clair, postgres, redis, objectstorage, etc.)
- **Managed vs Unmanaged**: Operator-managed vs user-provided components

## Conventions

- Follow controller-runtime patterns
- CRD changes require `make generate && make manifests`
- Test with kind/minikube for local development
```

**GEMINI.md:**
```markdown
# GEMINI

Please follow instructions from @./AGENTS.md
```

---

### quay/container-security-operator (CSO)

**AGENTS.md:**
```markdown
# Container Security Operator - Developer Agent Context

## Project Overview

Kubernetes Operator that scans container images for vulnerabilities using Quay's security scanning.
Creates ImageManifestVuln resources for discovered CVEs.

## Tech Stack

- **Language**: Go 1.21+
- **Framework**: controller-runtime
- **CRDs**: ImageManifestVuln
- **Integration**: Quay API, Clair

## Core Workflow

```bash
make build          # Build binary
make test           # Run tests
make docker-build   # Build container

# Generate CRD code
make generate
```

## Directory Structure

```
apis/secscan/v1alpha1/   # ImageManifestVuln CRD
cmd/                     # Main entrypoint
labeller/                # Pod labeling logic
secscan/                 # Security scan client
k8sutils/                # Kubernetes utilities
prometheus/              # Metrics
```

## Key Concepts

- Watches Pods for container images
- Queries Quay for vulnerability data
- Creates ImageManifestVuln resources per image
- Labels Pods with vulnerability counts
```

---

### quay/quay-bridge-operator (QBO)

**AGENTS.md:**
```markdown
# Quay Bridge Operator - Developer Agent Context

## Project Overview

Kubernetes Operator that integrates OpenShift with Quay for seamless image management.
Syncs OpenShift ImageStreams with Quay repositories.

## Tech Stack

- **Language**: Go 1.21+
- **Framework**: Operator SDK / controller-runtime
- **CRDs**: QuayIntegration
- **Integration**: OpenShift ImageStreams, Quay API

## Core Workflow

```bash
make build          # Build binary
make test           # Run tests
make deploy         # Deploy to cluster
make docker-build   # Build container
```

## Directory Structure

```
api/v1/              # QuayIntegration CRD
controllers/         # Reconciliation logic
pkg/                 # Business logic
  ├── client/        # Quay API client
  └── webhook/       # Admission webhooks
```

## Key Concepts

- **QuayIntegration CR**: Configures Quay-OpenShift integration
- Syncs namespaces to Quay organizations
- Creates robot accounts for image pull secrets
- Watches builds for automatic image management
```

---

### quay/mirror-registry

**AGENTS.md:**
```markdown
# Mirror Registry - Developer Agent Context

## Project Overview

CLI tool for deploying a minimal Quay instance for air-gapped OpenShift installations.
Packages Quay, PostgreSQL, and Redis for single-node deployment.

## Tech Stack

- **Language**: Go (CLI), Ansible (deployment)
- **Runtime**: Podman/Docker
- **Components**: Quay, PostgreSQL, Redis (all containerized)

## Core Workflow

```bash
make build          # Build CLI binary
make test           # Run tests
make release        # Build release artifacts

# Usage
./mirror-registry install --quayHostname registry.example.com
./mirror-registry uninstall
./mirror-registry upgrade
```

## Directory Structure

```
cmd/                 # CLI commands (install, uninstall, upgrade)
ansible-runner/      # Ansible playbooks for deployment
  ├── env/           # Ansible environment
  └── project/       # Playbooks and roles
test/                # Test suites
```

## Key Concepts

- Self-contained deployment (no external dependencies)
- Generates TLS certificates automatically
- Stores data in local directories (configurable)
- Supports air-gapped environments
```

---

## Next Steps

1. **Create PRs for other repos** - Use templates above as starting point
2. **Adjust templates** - Each repo maintainer should review and customize
3. **Add .claude/docs/** - For complex repos, add progressive disclosure docs
4. **Test with agents** - Verify documentation works with Claude/Gemini
