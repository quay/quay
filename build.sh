#!/usr/bin/env bash

set -e

if [[ -n "$(git status --porcelain)" ]]; then
  echo 'dirty build not supported' >&2
  exit 1
fi

# get named head (ex: branch, tag, etc..)
NAME="$( git rev-parse --abbrev-ref HEAD )"

# get 7-character sha
SHA=$( git rev-parse --short HEAD )

# checkout commit so .git/HEAD points to full sha (used in Dockerfile)
git checkout $SHA

REPO=quay.io/quay/quay:$SHA

# Use buildah or podman or docker 
if [ -x /usr/bin/buildah ]; then
	BUILDER="/usr/bin/buildah bud"
elif [ -x /usr/bin/podman ]; then
	BUILDER="/usr/bin/podman build"
elif [ -x /usr/bin/docker ] ; then
	BUILDER="/usr/bin/docker build"
fi
echo $BUILDER 

$BUILDER -t $REPO .
echo $REPO

git checkout "$NAME"
