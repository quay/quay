# Database & Migrations

## Database Stack

- **PostgreSQL 12.1** - Primary database
- **SQLAlchemy** - ORM
- **Alembic** - Migrations
- **Redis** - Caching, sessions, build logs

## Key Models

Located in `data/model/`:

- `user.py` - User, FederatedLogin, Team, TeamMember
- `repository.py` - Repository, RepositoryPermission, Star
- `tag.py` - Tag, TagManifest, ManifestLabel
- `image.py` - Image, ImageStorage, DerivedStorageForImage
- `organization.py` - Organization, OrganizationMember
- `build.py` - RepositoryBuild, RepositoryBuildTrigger
- `notification.py` - Notification, RepositoryNotification
- `appspecifictoken.py` - AppSpecificAuthToken
- `log.py` - LogEntry, LogEntry2, LogEntry3

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
    user = db.query(User).filter_by(username='admin').first()
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

- `data/database.py` - Database connection, session management
- `data/model/__init__.py` - Model imports
- `data/migrations/env.py` - Alembic environment
- `data/migrations/versions/` - Migration files
