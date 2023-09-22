#!/bin/bash
QUAYCONF=${QUAYCONF:-"$QUAYPATH/conf"}
QUAY_DIR=${QUAY_DIR:-"/quay-registry"}

echo "Validating rate limiting setup"
cd $QUAY_DIR
python $QUAYCONF/init/rate_limiting_validate_config.py

status=$?

if [ $status -ne 0 ];   then
    exit $status
fi
