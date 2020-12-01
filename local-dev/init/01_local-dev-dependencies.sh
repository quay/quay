#!/bin/bash 

set -e

QUAYDIR=${QUAYDIR:-"/"}

cd $QUAYDIR 

echo "[Local Dev] - Downloading AWS IP Ranges..."
curl -fsSL https://ip-ranges.amazonaws.com/ip-ranges.json -o util/ipresolver/aws-ip-ranges.json

echo "[Local Dev] - Building Front End..."
mkdir -p $QUAYDIR/static/webfonts && \
    mkdir -p $QUAYDIR/static/fonts && \
    mkdir -p $QUAYDIR/static/ldn && \
    PYTHONPATH=$QUAYPATH python -m external_libraries && \
    npm install --ignore-engines && \
    npm run watch &

cd -
