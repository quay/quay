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

## Common Pitfalls

### Tag `lifetime_end_ms` unique-constraint collision

The `Tag` table has a **unique index** on `(repository, name, lifetime_end_ms)`
(see `data/database.py`, `Tag.Meta.indexes`). This index prevents deadlocks
when concurrently moving and deleting tags, but it means that two rows with the
same `(repository, name)` pair **cannot share the same `lifetime_end_ms`
value**.

**Why this matters:** When expiring multiple tags at once, a bulk UPDATE like
`Tag.update(lifetime_end_ms=now_ms).where(...)` will raise an `IntegrityError`
if more than one matching row has the same `(repository, name)` — because the
UPDATE tries to give them all the same `lifetime_end_ms`.

**Established pattern — per-row collision avoidance:** Instead of a bulk UPDATE,
iterate over each tag individually and find an unoccupied `lifetime_end_ms`
value. The canonical implementation is in `remove_tag_from_timemachine()` in
`data/model/oci/tag.py`:

```python
# From remove_tag_from_timemachine() — iterate per row, decrementing
# by 1 ms each time to guarantee unique lifetime_end_ms values:
increment = 1
for tag in tags_to_update:
    Tag.update(lifetime_end_ms=now_ms - time_machine_ms - increment).where(
        Tag.id == tag
    ).execute()
    increment = increment + 1
```

A more defensive variant (used in `_expire_cosign_sibling_tags()` in the same
file) checks for existing rows before committing each value:

```python
# From _expire_cosign_sibling_tags() — check for occupied values:
increment = 0
for tag in matching_tags:
    while True:
        candidate_end = now_ms - increment
        occupied = (
            Tag.select(Tag.id)
            .where(
                Tag.repository == repo_id,
                Tag.name == tag.name,
                Tag.lifetime_end_ms == candidate_end,
                Tag.id != tag.id,
            )
            .exists()
        )
        if not occupied:
            break
        increment += 1
    Tag.update(lifetime_end_ms=candidate_end).where(Tag.id == tag.id).execute()
    increment += 1
```

**When writing or reviewing tag-expiry code**, always verify that the
`lifetime_end_ms` assignment produces a distinct value per
`(repository, name)` group. If a function expires multiple tags in a single
repository that could share a name, it **must** use one of the per-row patterns
above.

**Reference:** `data/model/oci/tag.py` —
`remove_tag_from_timemachine()`, `_expire_cosign_sibling_tags()`
