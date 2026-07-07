# Architecture & Patterns

## Backend Structure

```
├── app.py                    # Flask application factory
├── endpoints/
│   ├── api/                  # REST API v1
│   │   ├── __init__.py       # API setup, decorators, helpers
│   │   ├── repository.py     # Repository endpoints
│   │   ├── user.py           # User endpoints
│   │   ├── organization.py   # Organization endpoints
│   │   └── ...
│   ├── v2/                   # OCI/Docker Registry v2
│   │   ├── __init__.py       # V2 setup, decorators
│   │   ├── manifest.py       # Manifest operations
│   │   ├── blob.py           # Blob upload/download
│   │   ├── tag.py            # Tag listing
│   │   ├── catalog.py        # Repository catalog
│   │   ├── referrers.py      # OCI referrers API
│   │   └── v2auth.py         # Token authentication
│   └── decorators.py         # Shared permission decorators
├── data/
│   ├── database.py           # Peewee model class definitions (schema source of truth)
│   ├── model/                # Query and business-logic modules
│   │   ├── repository.py     # Repository queries
│   │   ├── user.py           # User and team queries
│   │   ├── blob.py           # Blob operations
│   │   ├── storage.py        # Storage management
│   │   ├── gc.py             # Garbage collection logic
│   │   ├── proxy_cache.py    # Pull-through cache config
│   │   ├── autoprune.py      # Auto-pruning policies
│   │   ├── namespacequota.py # Namespace quota enforcement
│   │   ├── immutability.py   # Tag immutability rules
│   │   ├── oci/              # OCI-specific model layer
│   │   │   ├── tag.py        # OCI tag operations
│   │   │   ├── manifest.py   # OCI manifest operations
│   │   │   └── blob.py       # OCI blob operations
│   │   └── sqlalchemybridge.py # Peewee-to-SQLAlchemy bridge for Alembic
│   ├── registry_model/       # Registry abstraction layer
│   │   ├── registry_oci_model.py # OCI registry implementation
│   │   └── datatypes.py      # Registry-level data types (Tag, Manifest, etc.)
│   └── migrations/           # Alembic migrations
├── auth/
│   ├── permissions.py        # Permission classes
│   ├── credentials.py        # Credential validation
│   └── registry_jwt_auth.py  # JWT for registry
├── features/
│   └── __init__.py           # Dynamic feature flag system
├── storage/
│   ├── cloud.py              # S3/GCS storage
│   ├── azurestorage.py       # Azure blob storage
│   ├── swift.py              # OpenStack Swift
│   └── local.py              # Local filesystem
└── workers/                  # Background processors
    ├── gc/                   # Garbage collection
    ├── repomirrorworker/     # Repository mirroring
    ├── securityworker/       # Clair integration
    ├── teamsyncworker/       # LDAP/Keystone team sync
    ├── autopruneworker.py    # Auto-pruning execution
    ├── storagereplication.py # Geo-replicated storage sync
    └── ...                   # ~25 workers total (see workers/)
```

## Data Layer

### Model Definitions vs. Query Modules

All Peewee model class definitions (User, Repository, Manifest, Tag,
ImageStorage, etc.) live in `data/database.py`. This is the schema source of
truth.

`data/model/` contains query and business-logic modules that operate on those
model classes. For example, `data/model/repository.py` has functions like
`get_repository()`.

`data/model/oci/` contains OCI-specific operations (tag listing, manifest
resolution, blob management).

### Registry Model Abstraction

`data/registry_model/` sits between the raw database models and v2 endpoints.
`registry_oci_model.py` implements the registry interface; `datatypes.py`
defines registry-level data types. The v2 endpoints consume this layer rather
than querying the database directly.

## Request Flow

```
Request → Flask → Middleware → Endpoint Decorator → Handler → Registry Model → Data Model → Database
                     │                  │
                     │                  └── Permission check (auth/permissions.py)
                     └── Auth validation (auth/credentials.py)
```

## Key Patterns

### Permission Decorators

```python
# endpoints/decorators.py
@require_repo_read    # Read access to repository
@require_repo_write   # Write access to repository
@require_repo_admin   # Admin access to repository
```

### Repository Access

```python
# endpoints/api/__init__.py
from endpoints.api import RepositoryParamResource

class MyEndpoint(RepositoryParamResource):
    # Automatically parses namespace/repository from URL
    def get(self, namespace, repository):
        repo = model.repository.get_repository(namespace, repository)
```

### Data Models

```python
# data/model/repository.py — uses Peewee query syntax
from data.database import Repository

def get_repository(namespace, repository):
    return (Repository
            .select()
            .where(Repository.namespace_user == namespace,
                   Repository.name == repository)
            .get_or_none())
```

### Error Handling

```python
# endpoints/exception.py
from endpoints.exception import NotFound, Unauthorized, InvalidRequest

if not repo:
    raise NotFound()
```

### Feature Flags

```python
# features/__init__.py dynamically injects boolean-like attributes from config
import features

if features.QUOTA_MANAGEMENT:
    # enforce quotas
```

#### Adding a New Feature Flag

When adding a new feature flag, update all of the following files:

1. **`config.py`** — Add the Python default value (e.g., `FEATURE_MY_FLAG = False`)
2. **`features/__init__.pyi`** — Add the type stub entry so editors and type checkers recognise the attribute
3. **`util/config/schema.py`** — Add a JSON schema property in `CONFIG_SCHEMA['properties']` (required by the Go Schema Drift Check — see step 4)
4. **`internal/config/features.go`** — Add a Go struct field with the corresponding `yaml` tag. If the flag is not consumed by Go code yet, add the key to `knownUnmapped` in `internal/config/schema_test.go` instead. The `TestSchemaFieldCoverage` test enforces bidirectional consistency between this file and `util/config/schema.py`; missing either side fails CI.
5. **Business logic module** — Add the `features.FLAG_NAME` guard in the relevant module (e.g., `data/model/organization.py`, `endpoints/api/organization.py`)
6. **Tests** — Add unit tests covering both flag-on and flag-off behaviour; add a Playwright e2e test if the flag affects user-facing behaviour

### Configuration Access

```python
# Runtime config via Flask's config dict
from app import app

db_uri = app.config.get('DB_URI')
```

Config is loaded from YAML (`local-dev/stack/config.yaml` on the host, mounted
to `conf/stack/config.yaml` inside the container) and validated against JSON
Schema in `config-tool/utils/generate/schema.json`.

## Workers

Background job processors in `workers/`. The table below lists key workers;
see the `workers/` directory for the complete set (~25 workers).

| Worker | Purpose |
|--------|---------|
| `gc/` | Garbage collection |
| `repomirrorworker/` | Repository mirroring |
| `securityworker/` | Clair vulnerability scanning |
| `buildlogsarchiver/` | Archive build logs |
| `notificationworker/` | Send notifications |
| `storagereplication.py` | Geo-replicate storage |
| `teamsyncworker/` | LDAP/Keystone team sync |
| `autopruneworker.py` | Execute auto-pruning policies |
| `quotaregistrysizeworker.py` | Calculate namespace quota usage |
| `namespacegcworker.py` | Namespace-level garbage collection |

Workers run as independent Gunicorn-managed processes. In local dev they
support hot-reload for faster iteration.

## Storage Backends

`storage/` implements multiple backends:

- `cloud.py` - S3, GCS, Cloudflare R2
- `azurestorage.py` - Azure Blob Storage
- `swift.py` - OpenStack Swift
- `local.py` - Local filesystem (simplest implementation, good reference for adding new backends)

`DistributedStorage` in `distributedstorage.py` handles failover and
geo-replication across backends at the application level.

## Cross-cutting Concerns

- **Quota management:** Namespace-level storage quotas enforced during v2 blob uploads. See `data/model/namespacequota.py`, `data/model/quota.py`, and the quota workers.
- **Proxy cache:** Pull-through caching from upstream registries. See `data/model/proxy_cache.py` and `workers/proxycacheblobworker.py`.
- **Auto-pruning:** Automated tag pruning policies per namespace. See `data/model/autoprune.py` and `workers/autopruneworker.py`.
- **Tag immutability:** Prevents tag overwrites. See `data/model/immutability.py`.
