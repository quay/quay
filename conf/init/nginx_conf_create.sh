#!/bin/bash

QUAYDIR=${QUAYDIR:-"/"}
QUAYPATH=${QUAYPATH:-"."}
QUAYCONF=${QUAYCONF:-"$QUAYPATH/conf"}

cd $QUAYDIR
python3 $QUAYCONF/init/nginx_conf_create.py
