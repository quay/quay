# Schema Migrations

SQL migration files applied by `quay db upgrade`.

Each file must contain a `-- revision: <alembic_id>` comment.
Files are applied in lexicographic filename order.
