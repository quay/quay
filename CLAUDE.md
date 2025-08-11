# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Project Quay is an enterprise-grade container registry that builds, stores, and distributes container images. It supports Docker Registry Protocol v2, OCI spec v1.1, and provides features like authentication, ACLs, team management, geo-replicated storage, security vulnerability analysis via Clair, and a Swagger-compliant HTTP API.

## Development Commands

### Local Development Environment

```bash
# Start Quay with basic components (PostgreSQL, Redis)
make local-dev-up

# Start Quay with Clair for vulnerability scanning
make local-dev-up-with-clair

# Rebuild and restart containers (hot-reload is supported)
make local-docker-rebuild

# Include Clair in rebuild
CLAIR=true make local-docker-rebuild

# Shut down the local environment
make local-dev-down
```

### Testing

```bash
# Run unit tests
make unit-test

# Run specific test module
TEST=true PYTHONPATH="." py.test test/path/to/test.py

# Run integration tests
make integration-test

# Run registry tests
make registry-test

# Run e2e tests
make e2e-test

# Run all tests
make test

# Run PostgreSQL-based tests
make test_postgres

# Run tests with coverage
TEST=true PYTHONPATH="." py.test --cov="." --cov-report=html -m 'not e2e' ./
```

### Code Quality

```bash
# Format code with Black
make black

# Run linting (TypeScript)
npm run lint

# Run type checking
make types-test

# Install pre-commit hooks
make install-pre-commit-hook
```

### Frontend Development

```bash
# Build frontend assets
npm run build

# Watch mode for frontend development
npm run watch

# Run frontend tests
npm run test

# Analyze bundle size
npm run analyze
```

## Architecture Overview

### Core Components

- **Registry Server** (`endpoints/v2/`): OCI/Docker registry implementation
- **API** (`endpoints/api/`): REST API for UI and programmatic access
- **Workers** (`workers/`): Background job processors for various tasks
- **Database Models** (`data/model/`): SQLAlchemy-based data models
- **Frontend** (`static/js/`, `web/`): TypeScript/Angular frontend

### Key Directories

- `data/`: Database models, migrations, and data access layer
- `endpoints/`: HTTP endpoints for registry, API, and web interfaces
- `workers/`: Background workers for tasks like garbage collection, mirroring
- `auth/`: Authentication and authorization implementations
- `storage/`: Storage backend implementations (S3, Azure, local, etc.)
- `buildman/`: Build manager for automated builds
- `notifications/`: Event notification system
- `util/`: Utility modules and helpers
- `web/`: Contains new PatternFly React UI
- `web/cypress/test/`: contains an db dump `quay-db-data.txt` for testing

### Database

The project uses PostgreSQL with Alembic for migrations. Key models include:
- Repository, Image, Tag, Manifest
- User, Team, Organization
- Build, BuildTrigger
- Notification, Log

### Configuration

Quay uses a YAML configuration file (`conf/stack/config.yaml` in local dev). Configuration is validated using JSON Schema defined in `config-tool/pkg/lib/config/schema.json`.

### Local Development URLs

- Quay UI: http://localhost:8080
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Clair (when enabled): localhost:6000 (from Quay container)

### Docker Compose Configuration

**Important**: For code changes to take effect in the container, ensure that the source code is mounted as a volume:

```yaml
# docker-compose.static should include:
volumes:
  - ".:/quay-registry"
  - "./local-dev/stack:/quay-registry/conf/stack"
```

Without the source code mount (`.:/quay-registry`), code changes will not be reflected in the running container, making debugging difficult. If code changes aren't taking effect, verify the volume mount and restart the container.

## Development Tips

1. The local environment supports hot-reload for both backend Python code and frontend TypeScript
2. Default superuser account is created with username 'admin' during first setup
3. Use `podman` or configure Docker for insecure registries when testing image push/pull
4. Frontend changes are automatically rebuilt via `npm watch` in the development container
5. Worker processes run as gunicorn workers in development for hot-reload support

## Global Read Only Superuser Implementation

### Configuration

Global Read Only Superusers are configured in the Quay config file:

```yaml
# conf/stack/config.yaml
SUPER_USERS:
  - admin
GLOBAL_READONLY_SUPER_USERS:
  - quayadmin
```

### Key Implementation Files

- `util/config/superusermanager.py`: Core user management, contains `is_global_readonly_superuser()`
- `auth/permissions.py`: Permission classes with global readonly support
- `endpoints/api/__init__.py`: Contains `allow_if_global_readonly_superuser()` helper and `allow_if_superuser()` (modified to exclude global readonly users from write operations)
- `endpoints/v2/__init__.py`: V2 API permission decorators with global readonly support

### API v1 Endpoint Support

Most API v1 endpoints support global readonly superusers via the `allow_for_global_readonly_superuser=True` parameter:

```python
@require_repo_read(allow_for_global_readonly_superuser=True)
def get_repository(namespace, repository):
    # Endpoint accessible to global readonly superusers
```

### API v2 Endpoint Support

V2 endpoints require explicit support via decorator parameters:

```python
@require_repo_read(allow_for_superuser=True, allow_for_global_readonly_superuser=True)
def list_tags(namespace_name, repo_name):
    # V2 endpoint accessible to global readonly superusers
```

### Write Operation Security

Global readonly superusers are blocked from write operations at multiple levels:

1. **Permission Classes**: Each write permission class (CreateRepositoryPermission, ModifyRepositoryPermission, etc.) checks and blocks global readonly superusers
2. **Superuser Function**: The `allow_if_superuser()` function excludes global readonly superusers from write privileges
3. **Endpoint Level**: Individual endpoints may have additional checks

### App Token Management

The app token endpoints provide different levels of access based on user permissions:

#### List App Tokens (`GET /api/v1/user/apptoken`)
- **Superusers**: Can see all tokens across the application
- **Global Read-Only Superusers**: Can see all tokens across the application (for auditing)
- **Regular Users**: Can only see their own tokens
- **Security**: Token codes are never included in list responses
- **Filtering**: Supports `?expiring=true` parameter

#### Individual App Token (`GET /api/v1/user/apptoken/<token_uuid>`)
- **Superusers**: Can access any user's token with full token_code
- **Global Read-Only Superusers**: Can access any user's token with full token_code
- **Regular Users**: Can only access their own tokens with full token_code

### Testing Global Read Only Superuser Features

```bash
# Test API v1 access
curl -s -b cookies.txt "http://localhost:8080/api/v1/repository/private/repo"

# Test API v2 access
TOKEN=$(curl -s -u quayadmin:password "http://localhost:8080/v2/auth?service=localhost:8080" | jq -r '.token')
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8080/v2/_catalog"

# Test app token list access (global readonly superuser sees all tokens)
curl -s -b cookies.txt "http://localhost:8080/api/v1/user/apptoken"

# Test individual app token access (global readonly superuser can access any token)
curl -s -b cookies.txt "http://localhost:8080/api/v1/user/apptoken/<token_uuid>"

# Test write blocking (should return insufficient_scope)
curl -s -b cookies.txt -X POST -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{"repository": "test/repo", "visibility": "private", "description": "should fail"}' \
  "http://localhost:8080/api/v1/repository"
```

## API Testing and Authentication

### Testing API Endpoints Against Running Instance

When testing API endpoints against a running Quay instance, use session-based authentication:

```bash
# 1. Get CSRF token and establish session
CSRF_TOKEN=$(curl -s -c cookies.txt -b cookies.txt "http://localhost:8080/csrf_token" | jq -r '.csrf_token')

# 2. Sign in with username/password
curl -s -c cookies.txt -b cookies.txt -X POST \
  -H "Content-Type: application/json" \
  -H "X-Requested-With: XMLHttpRequest" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{"username": "admin", "password": "password"}' \
  "http://localhost:8080/api/v1/signin"

# 3. Use session cookies for API calls
curl -s -b cookies.txt "http://localhost:8080/api/v1/user/" | jq '.username'
```

**Note**: Basic authentication (`curl -u user:pass`) does NOT work with the local dev instance for API v1. Always use session-based auth for API v1 testing.

### API v2 (Registry) Authentication

The API v2 endpoints (Docker Registry Protocol) use JWT bearer tokens for authentication:

```bash
# 1. Get bearer token for registry operations
TOKEN=$(curl -s -u username:password "http://localhost:8080/v2/auth?service=localhost:8080" | jq -r '.token')

# 2. Use bearer token for v2 API calls
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8080/v2/_catalog"

# 3. For specific repository access, include scope
TOKEN=$(curl -s -u username:password "http://localhost:8080/v2/auth?service=localhost:8080&scope=repository:namespace/repo:pull" | jq -r '.token')
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8080/v2/namespace/repo/tags/list"
```

**Key Differences**:
- API v1 (`/api/v1/*`): Uses session-based authentication with CSRF tokens
- API v2 (`/v2/*`): Uses JWT bearer tokens obtained via `/v2/auth` endpoint
- v2 auth supports scopes for fine-grained access control (pull, push, etc.)

### Restarting Quay During Development

When making code changes to the running application, restart the Quay container:

```bash
# Restart Quay to apply code changes
podman restart quay-quay

# Wait a few seconds, then verify it's running
curl -s "http://localhost:8080/api/v1/repository?public=true" | jq '.repositories | length'

# View container logs for debugging
podman logs quay-quay | tail -50
```

## Common Development Tasks

### Adding a New API Endpoint

1. Add the endpoint to the appropriate file in `endpoints/api/`
2. Create model interface in `endpoints/api/*_models_interface.py`
3. Implement the model in `endpoints/api/*_models_pre_oci.py`
4. Add tests in `test/` directory

### Modifying Database Schema

1. Make changes to models in `data/model/`
2. Generate migration: `alembic revision -m "description"`
3. Edit the generated migration file
4. Apply migration: `alembic upgrade head`

### Working with Storage Backends

Storage implementations are in `storage/`. The `DistributedStorage` class handles failover between multiple backends. Common backends include S3, Azure, Swift, and local filesystem.

### Background Workers

Workers are defined in `workers/` and handle tasks like:
- Garbage collection (`gcworker.py`)
- Repository mirroring (`repomirrorworker.py`)
- Security scanning (`securityworker.py`)
- Build log archiving (`buildlogsarchiver.py`)

## Testing with Container Images

### Pushing Test Images to Local Registry

To properly test v2 API functionality, you need actual container images in the registry:

```bash
# 1. Pull a test image
podman pull hello-world

# 2. Login to local registry
podman login localhost:8080 -u admin -p password --tls-verify=false

# 3. Tag and push to create test repository
podman tag hello-world localhost:8080/admin/testimage:latest
podman push localhost:8080/admin/testimage:latest --tls-verify=false

# 4. Verify via v2 API
TOKEN=$(curl -s -u admin:password "http://localhost:8080/v2/auth?service=localhost:8080" | jq -r '.token')
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8080/v2/_catalog"
```

**Note**: The `--tls-verify=false` flag is required for local development since the registry uses HTTP instead of HTTPS.
