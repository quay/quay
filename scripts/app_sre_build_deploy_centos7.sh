#!/bin/bash

# AppSRE team CD

set -exv

CURRENT_DIR=$(dirname $0)

BASE_IMG="quay"
QUAY_IMAGE="quay.io/app-sre/${BASE_IMG}"
IMG="${BASE_IMG}:latest"

GIT_HASH=`git rev-parse --short=7 HEAD`

# build the image
BUILD_CMD="docker build" IMG="$IMG" make app-sre-docker-build-centos7

# push the image
skopeo copy --dest-creds "${QUAY_USER}:${QUAY_TOKEN}" \
    "docker-daemon:${IMG}" \
    "docker://${QUAY_IMAGE}:latest"

skopeo copy --dest-creds "${QUAY_USER}:${QUAY_TOKEN}" \
    "docker-daemon:${IMG}" \
    "docker://${QUAY_IMAGE}:${GIT_HASH}"
