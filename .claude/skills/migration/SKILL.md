---
name: migration
description: >
  Create an Alembic database migration. Scaffolds the file via `alembic revision`,
  guides implementation of upgrade() and downgrade(), and validates the migration
  runs cleanly in both directions. Never writes migration files from scratch.
argument-hint: "\"description of schema change\""
allowed-tools:
  - Bash(alembic *)
  - Bash(git *)
  - Bash(make *)
  - Bash(TEST=true PYTHONPATH="." pytest *)
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
---

# Create Alembic Migration

Create a database migration for: `$ARGUMENTS`

**Never write migration files from scratch.** Always scaffold first — hand-crafted
revision IDs cause conflicts when multiple contributors independently generate migrations.

## Step 1: Scaffold the migration file

```bash
alembic revision -m "$ARGUMENTS"
```

Note the generated file path in `data/migrations/versions/`. Open it.

## Step 2: Read the generated file

Read the scaffolded file. It will have:
- A `revision` ID (auto-generated — do not change)
- A `down_revision` pointing to the previous migration
- Empty `upgrade()` and `downgrade()` functions to fill in

## Step 3: Implement upgrade() and downgrade()

Edit the scaffolded file. Common patterns:

### Adding a column

```python
def upgrade():
    op.add_column('table_name', sa.Column('column_name', sa.String(255), nullable=True))

def downgrade():
    op.drop_column('table_name', 'column_name')
```

### Adding a table

```python
def upgrade():
    op.create_table(
        'new_table',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
    )

def downgrade():
    op.drop_table('new_table')
```

### Adding an index

```python
def upgrade():
    op.create_index('ix_table_column', 'table_name', ['column_name'])

def downgrade():
    op.drop_index('ix_table_column', 'table_name')
```

### SQLite compatibility (for tests)

Wrap column modifications in `op.batch_alter_table()`:

```python
def upgrade():
    with op.batch_alter_table('table_name') as batch_op:
        batch_op.add_column(sa.Column('new_col', sa.Boolean(), nullable=True, server_default='false'))
        batch_op.alter_column('existing_col', nullable=False)

def downgrade():
    with op.batch_alter_table('table_name') as batch_op:
        batch_op.drop_column('new_col')
```

## Step 4: Validate upgrade

```bash
alembic upgrade head
```

Confirm it succeeds without errors.

## Step 5: Validate downgrade

```bash
alembic downgrade -1
```

Confirm the rollback works cleanly. A missing or no-op `downgrade()` will be
flagged by CodeRabbit's "Migration Downgrade Exists" pre-merge check.

## Step 6: Re-apply and test

```bash
alembic upgrade head
TEST=true PYTHONPATH="." pytest data/migrations/ -v
```

## Step 7: Report

Summarize:
- Migration file path and revision ID
- What `upgrade()` does
- What `downgrade()` does
- Validation results (upgrade + downgrade both succeeded)
- Next step: `/code` to implement model/endpoint changes, or `/pr` if migration is the only change
