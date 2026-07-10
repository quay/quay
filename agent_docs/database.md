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

## High-Impact Model Fields

Some database fields are read widely across the codebase. Before changing
their semantics (what values they store, their format, or their
nullability), you must trace all consumers and verify each one handles
the new semantics correctly. Failing to do so causes silent breakages in
unmodified code paths — the kind that only human reviewers catch late in
the review cycle.

**Motivation:** On PR #6160, a `User.email` semantic change (from real
email addresses to UUIDs for organization users) modified 25 files but
missed critical consumers in `workers/reconciliationworker.py` and
`endpoints/webhooks.py`. The PR was closed after 26 days of review.

### Widely-read fields

| Field | Key consumers to check |
|-------|------------------------|
| `User.email` | `workers/reconciliationworker.py` (marketplace customer ID lookup), `endpoints/webhooks.py` (invoice/payment notification recipient), `util/useremails.py` (email sending), `endpoints/api/user.py`, `endpoints/api/billing.py`, `oauth/login.py`, auth modules |
| `User.organization` | Organization-gated logic in `data/model/organization.py`, `data/model/repository.py`, `data/model/permission.py`, `auth/permissions.py`, `endpoints/api/` |
| `Repository.visibility` | Permission checks in `data/model/_basequery.py`, `data/model/repository.py`, registry endpoints in `endpoints/v2/`, `data/registry_model/` |

This table is not exhaustive — always grep to discover the full set of
consumers for any field you are changing.

### Checklist for field semantic changes

When changing what a database field stores (not just adding a new field):

1. **Find all readers:** `grep -rn 'model.field' --include='*.py'` and
   `grep -rn '.field' --include='*.py'` (dot-access patterns may not
   include the model name)
2. **Verify each reader** handles both old values (existing database
   records) and new values correctly
3. **Add a data migration** if existing records need updating to match
   the new semantics (see Migration Best Practices above)
4. **Update tests** that assert on the old field values — tests often
   hardcode expected values rather than referencing constants
5. **Document the behavioral change** in the PR description, listing
   every consumer you verified and how it handles the change

## Key Files

- `data/database.py` - Peewee model class definitions (schema source of truth)
- `data/model/` - Query and business-logic modules
- `data/model/oci/` - OCI-specific model operations
- `data/model/sqlalchemybridge.py` - Peewee-to-SQLAlchemy bridge for Alembic
- `data/registry_model/` - Registry abstraction layer between models and v2 endpoints
- `data/migrations/env.py` - Alembic environment
- `data/migrations/versions/` - Migration files
