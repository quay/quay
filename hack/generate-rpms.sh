#!/bin/bash

DOCKER="docker"
CONTAINER_DIR="/work"
BASE_IMAGE="registry.access.redhat.com/ubi8/ubi-minimal:latest"

$DOCKER run -it $BASE_IMAGE cat /etc/yum.repos.d/ubi.repo > ubi.repo

sed -i 's/ubi-9-codeready-builder/codeready-builder-for-ubi-9-$basearch/' ubi.repo
sed -i 's/\[ubi-9/[ubi-9-for-$basearch/' ubi.repo

curl https://raw.githubusercontent.com/konflux-ci/rpm-lockfile-prototype/refs/heads/main/Containerfile \
  | $DOCKER build -t localhost/rpm-lockfile-prototype -

$DOCKER run --rm -v ${PWD}:${CONTAINER_DIR} localhost/rpm-lockfile-prototype:latest --outfile=${CONTAINER_DIR}/rpms.lock.yaml --bare ${CONTAINER_DIR}/rpms.in.yaml
