#!/bin/bash
QUAYPATH=${QUAYPATH:-"."}
QUAYCONF=${QUAYCONF:-"$QUAYPATH/conf"}

set -e
cd ${QUAYDIR:-"/"}

# Run the database migration
REVISION_HEAD=$(PYTHONPATH=${QUAYPATH:-"."} python $QUAYCONF/init/data_migration.py)
PYTHONPATH=${QUAYPATH:-"."} alembic upgrade $REVISION_HEAD


# Run the database migration for plugins
PLUGIN_REVISION_HEAD="head"

function is_artifact_plugin() {
  PLUGIN_NAME=$1
  if [ -f $QUAYPATH/artifacts/plugins/$PLUGIN_NAME/alembic.ini ]; then
    return 0
  else
    return 1
  fi
}

function run_plugin_migration() {
  PLUGIN_NAME=$1
  cwd=$(pwd)
  cd $QUAYPATH/artifacts/plugins/$PLUGIN_NAME/
  PYTHONPATH=${QUAYPATH:-"."} alembic upgrade head
  cd $cwd
}

for plugin_name in $(ls $QUAYPATH/artifacts/plugins); do
  if is_artifact_plugin $plugin_name; then
    run_plugin_migration $plugin_name
  fi
done


