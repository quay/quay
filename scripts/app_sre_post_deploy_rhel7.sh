#!/bin/bash

# AppSRE team CD

set -exv

export DOCKER_CONF="$PWD/.docker"
mkdir -p "${DOCKER_CONF}"

BASE_IMG="quay"
IMG="${BASE_IMG}:latest"

GIT_HASH=`git rev-parse --short=7 HEAD`

# login to the backup repository
aws ecr get-login \
    --region ${AWS_REGION} --no-include-email | \
    sed 's/docker/docker --config="$DOCKER_CONF"/g' | \
    /bin/bash

# push the image
skopeo copy \
    --authfile "$DOCKER_CONF/config.json" \
    "docker-daemon:${IMG}" \
    "docker://${BACKUP_REPO_URL}:latest"

skopeo copy \
    --authfile "$DOCKER_CONF/config.json" \
    "docker-daemon:${IMG}" \
    "docker://${BACKUP_REPO_URL}:${GIT_HASH}"
