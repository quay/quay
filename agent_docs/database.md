# Database & Migrations

## Database Stack

- **PostgreSQL** - Primary database
- **Peewee** - ORM (model classes defined in `data/database.py`)
- **Alembic** - Migrations (via `data/model/sqlalchemybridge.py` which converts Peewee models to SQLAlchemy metadata)
- **Redis** - Caching, sessions, build logs

## Data Layer Structure

**Model class definitions** (User, Repository, Manifest, Tag, ImageStorage,
etc.) all live in `data/database.py`. This single file is the schema source of
truth.

**Query and business-logic modules** live in `data/model/`:

- `user.py` - User, FederatedLogin, Team, TeamMember queries
- `repository.py` - Repository, RepositoryPermission, Star queries
- `organization.py` - Organization, OrganizationMember queries
- `blob.py` - Blob operations
- `storage.py` - ImageStorage management
- `build.py` - RepositoryBuild, RepositoryBuildTrigger queries
- `notification.py` - Notification, RepositoryNotification queries
- `appspecifictoken.py` - AppSpecificAuthToken queries
- `log.py` - LogEntry queries
- `gc.py` - Garbage collection logic
- `proxy_cache.py` - Pull-through cache config
- `autoprune.py` - Auto-pruning policies
- `namespacequota.py` - Namespace quota enforcement
- `immutability.py` - Tag immutability rules
- `oci/` - OCI-specific operations (tag, manifest, blob, label)

## Schema Changes

### Creating a Migration

```bash
# Generate migration file
alembic revision -m "description_of_change"

# Edit the generated file in data/migrations/versions/
# Implement upgrade() and downgrade() functions
```

### Applying Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply to specific revision
alembic upgrade <revision_id>

# Rollback one migration
alembic downgrade -1
```

### Migration Best Practices

1. Always implement both `upgrade()` and `downgrade()`
2. Use `op.batch_alter_table()` for SQLite compatibility in tests
3. Test migrations in both directions
4. Include data migrations if needed (not just schema)

## Database Connection

```python
from data.database import db_transaction

# Use context manager for transactions
with db_transaction() as db:
    user = User.select().where(User.username == 'admin').get_or_none()
```

## Local Dev Database

- **Host:** localhost:5432
- **User:** quay
- **Password:** quay
- **Database:** quay
- **Connection:** `postgresql://quay:quay@quay-db/quay`

## Testing with Database

```bash
# Run tests with SQLite (default)
TEST=true PYTHONPATH="." pytest test/test_file.py -v

# Run tests with PostgreSQL
make test_postgres TESTS=test/test_file.py
```

## Key Files

- `data/database.py` - Peewee model class definitions (schema source of truth)
- `data/model/` - Query and business-logic modules
- `data/model/oci/` - OCI-specific model operations
- `data/model/sqlalchemybridge.py` - Peewee-to-SQLAlchemy bridge for Alembic
- `data/registry_model/` - Registry abstraction layer between models and v2 endpoints
- `data/migrations/env.py` - Alembic environment
- `data/migrations/versions/` - Migration files
