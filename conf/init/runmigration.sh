#!/bin/bash
QUAYPATH=${QUAYPATH:-"."}
QUAYCONF=${QUAYCONF:-"$QUAYPATH/conf"}

set -e
cd ${QUAYDIR:-"/"}

# Run the database migration
REVISION_HEAD=$(PYTHONPATH=${QUAYPATH:-"."} python $QUAYCONF/init/data_migration.py)
PYTHONPATH=${QUAYPATH:-"."} alembic upgrade $REVISION_HEAD
