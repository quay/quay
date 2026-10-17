#!/bin/bash
QUAYPATH=${QUAYPATH:-"."}
QUAYCONF=${QUAYCONF:-"$QUAYPATH/conf"}
QUAYSTACK=${QUAYSTACK:-"$QUAYCONF/stack"}
# IGNORE_VALIDATION= -> Set this variable to continue Quay boot after a failed config validation. 

if [ ! -f "$QUAYSTACK/config.yaml" ] && [ -f "/conf/stack/config.yaml" ]; then
    QUAYSTACK="/conf/stack"
fi

echo "Validating Configuration"
config-tool validate -c "$QUAYSTACK"/ --mode online

status=$?

if [ -z "${IGNORE_VALIDATION}" ]; then
    exit $status
else
    exit 0
fi
