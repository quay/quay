#!/usr/bin/env bash

QUAYDIR=${QUAYDIR:-"/"}
QUAYPATH=${QUAYPATH:-"."}
QUAYCONF=${QUAYCONF:-"$QUAYPATH/conf"}

cd $QUAYDIR

if [[ "$KUBERNETES_SERVICE_HOST" != "" ]];then
    echo "Running on kubernetes, attempting to retrieve extra certs from secret"
    python $QUAYCONF/init/02_get_kube_certs.py
fi
