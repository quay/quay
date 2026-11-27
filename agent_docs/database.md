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

### QuotaNamespaceSize / QuotaRepositorySize Backfill Lifecycle

`QuotaNamespaceSize` and `QuotaRepositorySize` use a two-field state machine
to track whether the stored `size_bytes` value is reliable:

| `backfill_complete` | `size_bytes` meaning |
|---------------------|----------------------|
| `True` | Accurate; safe to use for metrics, enforcement, and reporting |
| `False` | Transient `0`; undergoing recalculation — do **not** use |

**What triggers `backfill_complete=False`:** The row is reset to
`size_bytes=0, backfill_complete=False` by `reset_backfill()` /
`reset_namespace_backfill()` in `data/model/quota.py` whenever a tag push,
namespace invalidation, or explicit recomputation request arrives. A background
GC worker (`workers/`) then recalculates the true total and flips
`backfill_complete` back to `True`.

**The invariant — apply this every time you read `size_bytes`:** Any
production code path that reads `size_bytes` from `QuotaNamespaceSize` or
`QuotaRepositorySize` for metrics, quota enforcement, or reporting **must**
either:

1. Filter `backfill_complete=True` to exclude in-progress rows, **or**
2. Explicitly handle the incomplete case with a documented rationale explaining
   why exposing a `0` or stale value is acceptable.

Omitting the filter causes a namespace mid-backfill to appear as if it has zero
usage, making its available quota appear at 100% until recomputation finishes —
a correctness bug that is invisible in unit tests unless the test explicitly
creates `backfill_complete=False` rows.

**Canonical examples of the pattern in `data/model/quota.py`:**

- `_next_namespace_quota_candidate_ids()` — filters
  `QuotaNamespaceSize.backfill_complete == True` in the candidate-ID query
  so that mid-backfill namespaces are not selected as export candidates.
- `get_all_namespace_quota_data()` — adds `backfill_complete == True` to the
  `LEFT OUTER JOIN` condition on `QuotaNamespaceSize`, so incomplete rows
  yield `size_bytes=None` rather than `0`.
- `get_all_repository_sizes()` — filters `QuotaRepositorySize.backfill_complete
  == True` in the `WHERE` clause, excluding mid-backfill repositories
  entirely.

**Checklist for new quota-reading code:**

- [ ] Does every query that reads `size_bytes` from `QuotaNamespaceSize` or
  `QuotaRepositorySize` include a `backfill_complete=True` filter (or a
  documented rationale for omitting it)?
- [ ] Does the test file include a case that inserts a
  `backfill_complete=False` row and asserts the function skips it (or
  handles it explicitly)? See `test_quota_metrics_queries.py` for
  reference test patterns.

**Reference:** `data/model/quota.py` — `_next_namespace_quota_candidate_ids`,
`get_all_namespace_quota_data`, `get_all_repository_sizes`,
`reset_backfill`, `reset_namespace_backfill`; `data/model/test/test_quota_metrics_queries.py`
