#!/bin/bash
QUAYPATH=${QUAYPATH:-"."}
QUAYCONF=${QUAYCONF:-"$QUAYPATH/conf"}

set -e
cd ${QUAYDIR:-"/"}

# Run the database migration
REVISION_HEAD=$(python3 $QUAYCONF/init/data_migration.py)
alembic upgrade $REVISION_HEAD
