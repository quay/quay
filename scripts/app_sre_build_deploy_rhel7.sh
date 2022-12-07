#!/bin/bash

# AppSRE team CD

set -exv

CURRENT_DIR=$(dirname $0)

BASE_IMG="quay-py3"
IMG="${BASE_IMG}:latest"
BACKUP_BASE_IMG="quayio-py3-backup"
BACKUP_IMAGE="${BACKUP_URL}/${BACKUP_BASE_IMG}"

GIT_HASH=`git rev-parse --short=7 HEAD`

export REACT_APP_QUAY_DOMAIN=quay.io

# build the image
BUILD_CMD="docker build" IMG="$IMG" make app-sre-docker-build

# save the image as a tar archive
docker save ${IMG} -o ${BASE_IMG}

# push image to backup repository
skopeo copy --dest-creds "${BACKUP_USER}:${BACKUP_TOKEN}" \
    "docker-archive:${BASE_IMG}" \
    "docker://${BACKUP_IMAGE}:latest"

skopeo copy --dest-creds "${BACKUP_USER}:${BACKUP_TOKEN}" \
    "docker-archive:${BASE_IMG}" \
    "docker://${BACKUP_IMAGE}:${GIT_HASH}"
