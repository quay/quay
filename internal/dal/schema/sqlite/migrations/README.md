# Schema Migrations

SQL migration files applied by `quay db upgrade`.

Each file must contain a `-- revision: <id>` comment. Go-only SQLite
migrations also contain a `-- down_revision: <id>` comment and are applied by
following that revision chain.
