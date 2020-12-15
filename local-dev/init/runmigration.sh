#!/bin/bash
QUAYPATH=${QUAYPATH:-"."}
QUAYCONF=${QUAYCONF:-"$QUAYPATH/conf"}

set -e
cd ${QUAYDIR:-"/"}

# Run the database migration
PYTHONPATH=${QUAYPATH:-"."} python $QUAYCONF/init/data_migration.py > revision_head
PYTHONPATH=${QUAYPATH:-"."} alembic upgrade `cat revision_head`
