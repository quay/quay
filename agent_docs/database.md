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

## Concurrency Safety

Quay runs multiple worker processes and handles concurrent HTTP requests.
Any state transition that gates a side-effect (dedup, claim, lock) must
be **atomic**. Never use the check-then-act pattern (read state, decide,
write state) when multiple workers or requests could race on the same row.

### Preferred Patterns

**Atomic claim via conditional UPDATE.** Use `UPDATE ... WHERE` with a
condition that fails if another caller already claimed the row. Peewee
returns the number of rows updated, so a return value of 0 means the row
changed since you read it:

```python
# Read current state
state = MyModel.get_or_none(MyModel.id == row_id)

# Atomically claim — only succeeds if no one else changed the row
updated = (
    MyModel.update(status="claimed", claimed_at=now)
    .where(
        MyModel.id == state.id,
        MyModel.status == state.status,        # optimistic lock
        MyModel.claimed_at == state.claimed_at, # optimistic lock
    )
    .execute()
)
if updated == 0:
    # Another caller won the race — do not proceed
    return False
```

**IntegrityError on insert.** When a unique constraint protects against
duplicates, wrap `Model.create()` in `try/except IntegrityError`. This
handles the race where two callers both see "no row exists" and try to
insert simultaneously:

```python
from peewee import IntegrityError

try:
    MyModel.create(key=value, status="active")
except IntegrityError:
    # Another caller inserted first — the duplicate was prevented
    return False
```

**GlobalLock for worker-level mutual exclusion.** For coarse-grained
locking across processes (e.g., ensuring only one worker runs a
scheduled job), use `GlobalLock` from `util/locking.py`. Note that
Redis is not a tier-1 service, so `GlobalLock` should not be used for
critical request-path code:

```python
from util.locking import GlobalLock

with GlobalLock("my_worker_lock", lock_ttl=300):
    # Only one process runs this block at a time
    do_exclusive_work()
```

### Anti-pattern: Check-then-Act

The following pattern is **unsafe** under concurrency. Two workers can
both pass the check before either writes, producing duplicate
side-effects or hitting unique constraint errors:

```python
# BAD — race condition between read and write
state = MyModel.get_or_none(MyModel.key == value)
if state is None or state.status == "eligible":
    # Both Worker A and Worker B can reach this point
    MyModel.create(key=value, status="claimed")  # duplicate!
    enqueue_side_effect()  # fires twice!
```

Replace this with an atomic claim (conditional UPDATE) or
IntegrityError handling as shown above.

### Canonical Example

See `data/model/quota_notification_state.py` — specifically the
`claim_notification()` function — for a production example that
combines all three patterns:
- Atomic claim via `UPDATE ... WHERE` with optimistic locking on
  `last_notified_at` and `cleared`
- `IntegrityError` handling for the concurrent-insert race on
  first notification
- Read-only `should_notify()` separated from the atomic
  `claim_notification()` for callers that only need a check

## Key Files

- `data/database.py` - Peewee model class definitions (schema source of truth)
- `data/model/` - Query and business-logic modules
- `data/model/oci/` - OCI-specific model operations
- `data/model/sqlalchemybridge.py` - Peewee-to-SQLAlchemy bridge for Alembic
- `data/registry_model/` - Registry abstraction layer between models and v2 endpoints
- `data/migrations/env.py` - Alembic environment
- `data/migrations/versions/` - Migration files
