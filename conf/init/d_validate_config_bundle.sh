#!/bin/bash
QUAYPATH=${QUAYPATH:-"."}
QUAYCONF=${QUAYCONF:-"$QUAYPATH/conf"}
# IGNORE_VALIDATION= -> Set this variable to continue Quay boot after a failed config validation. 


echo "Validating Configuration"
config-tool validate -c $QUAYCONF/stack/ --mode online

status=$?

if [ -z "${IGNORE_VALIDATION}" ]; then
    exit $status
else
    exit 0
fi
