# Schema Migrations

SQL migration files applied by `quay db upgrade`.

The root file is the idempotent OMR squash bridge and contains a
`-- revision: <id>` comment. Every later file also contains a
`-- down_revision: <id>` comment; the Go migration runner follows that graph
from the database's exact Alembic or Go revision.
