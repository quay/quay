#!/bin/bash

# AppSRE team CD

set -exv

CURRENT_DIR=$(dirname $0)

BASE_IMG="quay"
IMG="${BASE_IMG}:latest"

GIT_HASH=`git rev-parse --short=7 HEAD`

# login to the backup repository
aws ecr get-login --region ${AWS_REGION} --no-include-email | /bin/bash

# push the image
skopeo copy \
    "docker-daemon:${IMG}" \
    "docker://${BACKUP_REPO_URL}:latest"

skopeo copy \
    "docker-daemon:${IMG}" \
    "docker://${BACKUP_REPO_URL}:${GIT_HASH}"
