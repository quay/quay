#!/bin/bash

# AppSRE team CD

set -exv

BASE_IMG="quay-py3"
IMG="${BASE_IMG}:latest"
BACKUP_BASE_IMG="quayio-py3-backup"
BACKUP_IMAGE="${BACKUP_URL}/${BACKUP_BASE_IMG}"

GIT_HASH=`git rev-parse --short=7 HEAD`

# push the image to backup repository
skopeo copy --dest-creds "${BACKUP_USER}:${BACKUP_TOKEN}" \
    "docker-archive:${BASE_IMG}" \
    "docker://${BACKUP_IMAGE}:latest"

skopeo copy --dest-creds "${BACKUP_USER}:${BACKUP_TOKEN}" \
    "docker-archive:${BASE_IMG}" \
    "docker://${BACKUP_IMAGE}:${GIT_HASH}"

# remove the archived image
rm ${BASE_IMG}
