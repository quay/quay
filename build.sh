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
docker build -t $REPO .
echo $REPO

git checkout "$NAME"
