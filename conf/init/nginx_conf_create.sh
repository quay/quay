#!/bin/bash

QUAYDIR=${QUAYDIR:-"/"}
QUAYPATH=${QUAYPATH:-"."}
QUAYCONF=${QUAYCONF:-"$QUAYPATH/conf"}

cd $QUAYDIR
python $QUAYCONF/init/nginx_conf_create.py
