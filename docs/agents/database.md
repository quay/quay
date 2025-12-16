# Database Architecture

## Overview

Quay uses Peewee ORM with PostgreSQL (primary) or MySQL. Redis handles caching and queuing.

### Peewee + Alembic

Quay uses two database libraries for different purposes:

| Library | Purpose | Location |
|---------|---------|----------|
| **Peewee** | Runtime ORM for all queries, inserts, updates | `data/database.py`, `data/model/` |
| **Alembic** | Database schema migrations | `data/migrations/` |

Alembic is designed for SQLAlchemy, not Peewee. The bridge at `data/model/sqlalchemybridge.py` converts Peewee model definitions into SQLAlchemy metadata that Alembic can understand. This allows Quay to use Peewee's simpler ORM for runtime operations while leveraging Alembic's mature migration tooling.

For authoritative guidance, see `data/database.py` for model definitions and `data/migrations/` for migration implementation.

## Core Models

### User & Organization

| Model | Purpose |
|-------|---------|
| `User` | User accounts |
| `FederatedLogin` | External auth (LDAP, OIDC) |
| `Team` | Organization teams |
| `TeamMember` | Team membership |

See: `data/database.py`: `User`, `FederatedLogin`, `Team`, `TeamMember` classes

### Repository & Images

| Model | Purpose |
|-------|---------|
| `Repository` | Container repositories |
| `RepositoryTag` | Named tags |
| `Manifest` | OCI manifests |
| `ManifestBlob` | Manifest layer references |
| `ImageStorage` | Blob storage metadata |

See: `data/database.py`: `Repository`, `RepositoryTag`, `Manifest`, `ManifestBlob`, `ImageStorage` classes

### Permissions

| Model | Purpose |
|-------|---------|
| `RepositoryPermission` | User/team repo access |
| `TeamRole` | Team roles in org |

See: `data/database.py`: `RepositoryPermission`, `TeamRole` classes

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

See: `data/database.py`: `UseThenDisconnect` class, `configure()` function

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
