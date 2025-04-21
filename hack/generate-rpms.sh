#!/bin/bash

DOCKER="docker"
CONTAINER_DIR="/work"
BASE_IMAGE="registry.access.redhat.com/ubi8/ubi-minimal:latest"

curl https://raw.githubusercontent.com/konflux-ci/rpm-lockfile-prototype/refs/heads/main/Containerfile \
  | $DOCKER build -t localhost/rpm-lockfile-prototype -

$DOCKER run --rm -v ${PWD}:${CONTAINER_DIR} localhost/rpm-lockfile-prototype:latest --outfile=${CONTAINER_DIR}/rpms.lock.yaml --image=${BASE_IMAGE} ${CONTAINER_DIR}/rpms.in.yaml
