#! /bin/sh
QUAYPATH=${QUAYPATH:-"."}
QUAYCONF=${QUAYCONF:-"$QUAYPATH/conf"}

echo "Validating Configuration"
config-tool validate -c $QUAYCONF/stack/ --mode online
