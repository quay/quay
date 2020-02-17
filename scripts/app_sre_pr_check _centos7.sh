#!/bin/bash
set -exv

BASE_IMG="quay"

IMG="${BASE_IMG}:latest"

BUILD_CMD="docker build" IMG="$IMG" make app-sre-docker-build-centos7
