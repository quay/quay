# Database Architecture

## Overview

Quay uses Peewee ORM with PostgreSQL (primary) or MySQL. Redis handles caching and queuing.

## Core Models

### User & Organization

| Model | Purpose |
|-------|---------|
| `User` | User accounts |
| `FederatedLogin` | External auth (LDAP, OIDC) |
| `Team` | Organization teams |
| `TeamMember` | Team membership |

See: `data/database.py:788-881` (User), `data/database.py:963-988` (Team)

### Repository & Images

| Model | Purpose |
|-------|---------|
| `Repository` | Container repositories |
| `RepositoryTag` | Named tags |
| `Manifest` | OCI manifests |
| `ManifestBlob` | Manifest layer references |
| `ImageStorage` | Blob storage metadata |

See: `data/database.py:1056-1106` (Repository), `data/database.py:1875-1946` (Manifest/Tag)

### Permissions

| Model | Purpose |
|-------|---------|
| `RepositoryPermission` | User/team repo access |
| `TeamRole` | Team roles in org |

See: `data/database.py:1160-1172`

## Business Logic (data/model/)

Always use `data/model/` functions instead of direct DB queries:

| Module | Purpose |
|--------|---------|
| `data/model/repository.py` | Repository CRUD operations |
| `data/model/user.py` | User management |
| `data/model/tag.py` | Tag operations |
| `data/model/team.py` | Team management |
| `data/model/permission.py` | Permission handling |
| `data/model/blob.py` | Blob operations |

## Migrations

```bash
# Create new migration
PYTHONPATH=. alembic revision -m "Add new column"

# Run migrations
PYTHONPATH=. alembic upgrade head

# Check current version
PYTHONPATH=. alembic current
```

See: `data/migrations/versions/`

## Database Connection

| Class/Function | Purpose |
|----------------|---------|
| `UseThenDisconnect` | Context manager for worker processes |
| `configure()` | Database configuration |

See: `data/database.py:320-335` (UseThenDisconnect), `data/database.py:601` (configure)

## Redis Caching

| Module | Purpose |
|--------|---------|
| `data/cache/impl.py` | Cache implementation |
| `data/cache/cache_key.py` | Cache key generation |
| `data/cache/redis_cache.py` | Redis-specific caching |

See: `data/cache/`

## Testing

```bash
# Run with PostgreSQL (recommended)
make test_postgres TESTS=data/model/test/

# Set up test database
export TEST_DATABASE_URI="postgresql://quay:quay@localhost:5433/quay"
make full-db-test
```

See: `data/test/`, `data/model/test/`

For test patterns and examples, see: `docs/agents/testing.md`
