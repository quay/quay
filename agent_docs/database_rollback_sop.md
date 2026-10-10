# Database Migration Rollback — Standard Operating Procedure

## Overview

This document covers how to safely roll back (downgrade) an Alembic database migration in Quay. It was created as part of a POC using a dummy `poc_rollback_demo` table and the `tools/db_rollback.py` automation script.

## Table of Contents

1. [Background](#background)
2. [POC Walkthrough](#poc-walkthrough)
3. [Manual Rollback Steps](#manual-rollback-steps)
4. [Automated Rollback (Recommended)](#automated-rollback-recommended)
5. [Stage Environment Procedure](#stage-environment-procedure)
6. [Troubleshooting](#troubleshooting)

---

## Background

- Quay uses **Alembic** for schema migrations (`data/migrations/versions/`).
- CICD automatically runs `alembic upgrade head` on deployment.
- There is **no automated downgrade path** — rollbacks are manual.
- Every migration file must implement both `upgrade()` and `downgrade()`.
- The current revision is stored in the `alembic_version` table (single row).

### Key files

| File | Purpose |
|------|---------|
| `alembic.ini` | Alembic configuration |
| `data/migrations/env.py` | Runtime environment (DB URL resolution, engine creation) |
| `data/migrations/versions/` | Migration scripts |
| `tools/db_rollback.py` | Rollback automation script (this POC) |

---

## POC Walkthrough

### What we're doing

1. A dummy migration (`a1b2c3d4e5f7`) creates a `poc_rollback_demo` table.
2. CICD deploys to stage → `alembic upgrade head` runs → table is created.
3. We then manually execute a downgrade to remove the table, verifying the full rollback process.

### The dummy migration

**File:** `data/migrations/versions/a1b2c3d4e5f7_add_poc_rollback_demo_table.py`

- **upgrade:** Creates `poc_rollback_demo` table with `id`, `name`, `description`, `created_at` columns and a unique index on `name`.
- **downgrade:** Drops the index and then the table.
- **Depends on:** `15f06d00c4b3` (the current head at time of writing).

### Step-by-step POC execution

```
1. Merge the migration to main/master
2. CICD deploys to stage (alembic upgrade head runs automatically)
3. Verify: connect to stage DB and confirm the table exists
4. Run the rollback (see sections below)
5. Verify: confirm the table is gone and alembic_version is reverted
```

---

## Manual Rollback Steps

Use these when you cannot run the automation script (e.g., restricted environments).

### Prerequisites

- Shell access to a Quay pod or a host that can reach the database.
- `PYTHONPATH` set to the Quay repo root.
- Quay config available (typically at `conf/stack/config.yaml`).

### 1. Check current state

```bash
# From inside the Quay container / pod:
PYTHONPATH=. alembic current
```

Expected output includes the current revision hash, e.g., `a1b2c3d4e5f7 (head)`.

You can also check directly in PostgreSQL:

```sql
SELECT version_num FROM alembic_version;
```

### 2. Verify the downgrade target

Look at the migration file to confirm what `down_revision` points to:

```bash
head -12 data/migrations/versions/a1b2c3d4e5f7_add_poc_rollback_demo_table.py
```

You should see `down_revision = "15f06d00c4b3"`.

### 3. Preview the downgrade SQL (dry run)

```bash
PYTHONPATH=. alembic downgrade -1 --sql
```

This prints the SQL without executing it. Review carefully.

### 4. Execute the downgrade

```bash
# Roll back 1 step
PYTHONPATH=. alembic downgrade -1

# OR roll back to a specific revision
PYTHONPATH=. alembic downgrade 15f06d00c4b3
```

### 5. Verify

```bash
PYTHONPATH=. alembic current
# Should show: 15f06d00c4b3
```

```sql
-- Confirm the table is gone
SELECT tablename FROM pg_tables WHERE tablename = 'poc_rollback_demo';
-- Should return 0 rows

-- Confirm alembic_version
SELECT version_num FROM alembic_version;
-- Should return: 15f06d00c4b3
```

---

## Automated Rollback (Recommended)

The `tools/db_rollback.py` script wraps the manual steps with safety checks, a confirmation prompt, dry-run support, and post-rollback verification.

### Quick reference

```bash
# All commands assume PYTHONPATH=. and are run from the Quay repo root.

# 1. Check current migration state
PYTHONPATH=. python tools/db_rollback.py --status

# 2. View full migration history
PYTHONPATH=. python tools/db_rollback.py --history

# 3. Dry-run (preview SQL, no changes)
PYTHONPATH=. python tools/db_rollback.py --dry-run --steps 1

# 4. Roll back 1 migration (with confirmation prompt)
PYTHONPATH=. python tools/db_rollback.py --steps 1

# 5. Roll back to a specific revision
PYTHONPATH=. python tools/db_rollback.py --target 15f06d00c4b3

# 6. Roll back without confirmation (for scripted pipelines)
PYTHONPATH=. python tools/db_rollback.py --steps 1 --yes

# 7. Override DB connection string
PYTHONPATH=. python tools/db_rollback.py --steps 1 --db-uri 'postgresql://user:pass@host:5432/quay'
```

### What the script does

1. **Pre-flight checks** — reads `alembic_version`, resolves the target revision, prints a summary.
2. **Confirmation prompt** — requires `y` to proceed (skip with `--yes`).
3. **Downgrade execution** — calls `alembic.command.downgrade()`.
4. **Post-rollback verification** — re-reads `alembic_version` and confirms it matches the target.

### Dry-run output example

```
  DRY-RUN — SQL that would be executed:
  ============================================================
  DROP INDEX poc_rollback_demo_name;
  DROP TABLE poc_rollback_demo;
  UPDATE alembic_version SET version_num='15f06d00c4b3' WHERE ...;
  ============================================================
```

---

## Stage Environment Procedure

### Before you start

1. **Notify the team** — post in the relevant channel that you're performing a DB rollback on stage.
2. **Confirm no active deployments** — ensure CICD is not mid-deploy (it would re-run `upgrade head` and undo your downgrade).
3. **Take a DB snapshot** — if your stage environment supports it, snapshot the RDS/CloudSQL instance first.

### Execution (from a Quay pod)

```bash
# 1. Exec into a Quay pod
oc rsh <quay-pod-name>
# or
kubectl exec -it <quay-pod-name> -- /bin/bash

# 2. Check current state
PYTHONPATH=/quay-registry python /quay-registry/tools/db_rollback.py --status

# 3. Dry-run
PYTHONPATH=/quay-registry python /quay-registry/tools/db_rollback.py --dry-run --steps 1

# 4. Execute rollback
PYTHONPATH=/quay-registry python /quay-registry/tools/db_rollback.py --steps 1

# 5. Verify (also check directly in psql if possible)
PYTHONPATH=/quay-registry python /quay-registry/tools/db_rollback.py --status
```

### After rollback

1. **Prevent CICD from re-upgrading.** The next deployment will run `alembic upgrade head` and re-apply the migration you just rolled back. Options:
   - Revert the migration file from the branch/release before redeploying.
   - Or gate the deployment until the migration fix is merged.
2. **Verify application health** — confirm Quay pods are running, API responds, and no errors in logs related to missing tables/columns.

---

## Troubleshooting

### `alembic_version` table is missing

The database was never initialized with Alembic. You'll need to stamp it:

```bash
PYTHONPATH=. alembic stamp <known_good_revision>
```

### Downgrade fails mid-way

The `transactional_ddl` setting in `env.py` is `False` for online mode, meaning **DDL statements are not wrapped in a transaction on PostgreSQL** (PostgreSQL actually supports transactional DDL, but Quay disables it). If a downgrade fails partway:

1. Check which DDL statements already executed (inspect the schema).
2. Manually complete or revert the remaining steps.
3. Update `alembic_version` to the correct revision:
   ```sql
   UPDATE alembic_version SET version_num = '<correct_revision>';
   ```

### CICD re-applied the migration after rollback

The deployment pipeline runs `alembic upgrade head`. If you rolled back but a new deploy happened, the migration is re-applied. To prevent this:
- Remove or revert the migration file from the release branch before deploying.

### "No such revision" error

This happens when the `alembic_version` table references a revision that doesn't exist in the codebase (e.g., you rolled back to a revision from a different branch). Fix by stamping:

```bash
PYTHONPATH=. alembic stamp <revision_that_exists>
```

---

## Cleanup

After the POC is validated, remove the dummy migration:

```bash
rm data/migrations/versions/a1b2c3d4e5f7_add_poc_rollback_demo_table.py
```

If the table was created in any environment, drop it manually:

```sql
DROP TABLE IF EXISTS poc_rollback_demo;
UPDATE alembic_version SET version_num = '15f06d00c4b3';
```
