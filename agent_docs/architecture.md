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
│   │   ├── blob.py           # Blob operations
│   │   └── ...
│   └── decorators.py         # Shared permission decorators
├── data/
│   ├── database.py           # DB connection, session
│   ├── model/                # SQLAlchemy models
│   └── migrations/           # Alembic migrations
├── auth/
│   ├── permissions.py        # Permission classes
│   ├── credentials.py        # Credential validation
│   └── registry_jwt_auth.py  # JWT for registry
├── storage/
│   ├── cloud.py              # S3/GCS storage
│   ├── azurestorage.py       # Azure blob storage
│   ├── swift.py              # OpenStack Swift
│   └── local.py              # Local filesystem
└── workers/                  # Background processors
    ├── gcworker/             # Garbage collection
    ├── repomirrorworker/     # Repository mirroring
    └── securityworker/       # Clair integration
```

## Request Flow

```
Request → Flask → Middleware → Endpoint Decorator → Handler → Model → Database
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
# data/model/repository.py
from data.database import db

def get_repository(namespace, repository):
    return Repository.query.filter_by(
        namespace_user=namespace,
        name=repository
    ).first()
```

### Error Handling

```python
# endpoints/exception.py
from endpoints.exception import NotFound, Unauthorized, InvalidRequest

if not repo:
    raise NotFound()
```

## Workers

Background job processors in `workers/`:

| Worker | Purpose |
|--------|---------|
| `gcworker` | Garbage collection |
| `repomirrorworker` | Repository mirroring |
| `securityworker` | Clair vulnerability scanning |
| `buildlogsarchiver` | Archive build logs |
| `notificationworker` | Send notifications |
| `storagereplication` | Geo-replicate storage |

Workers run as gunicorn sub-processes in local dev for hot-reload.

## Storage Backends

`storage/` implements multiple backends:

- `cloud.py` - S3, GCS, Cloudflare R2
- `azurestorage.py` - Azure Blob Storage
- `swift.py` - OpenStack Swift
- `local.py` - Local filesystem

`DistributedStorage` in `distributedstorage.py` handles failover between backends.

## Configuration

```python
# config.py - Configuration loading
from util.config import config

# Access config values
db_uri = config.get('DB_URI')
```

Config validated against JSON Schema in `config-tool/utils/generate/schema.json`.
