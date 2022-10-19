#!/bin/bash

# AppSRE team CD

set -exv

BASE_IMG="quay-py3"
IMG="${BASE_IMG}:latest"
QUAY_IMAGE="quay.io/app-sre/${BASE_IMG}"

GIT_HASH=`git rev-parse --short=7 HEAD`

# push the image
skopeo copy --dest-creds "${QUAY_USER}:${QUAY_TOKEN}" \
    "docker-archive:${BASE_IMG}" \
    "docker://${QUAY_IMAGE}:latest"

skopeo copy --dest-creds "${QUAY_USER}:${QUAY_TOKEN}" \
    "docker-archive:${BASE_IMG}" \
    "docker://${QUAY_IMAGE}:${GIT_HASH}"

# remove the archived image
rm ${BASE_IMG}