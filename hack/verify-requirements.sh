#!/bin/sh -eu
TMP=$(mktemp -d "${TMPDIR:-/tmp/}quay-verify-requirements.XXXXXXXX")
TMP_PACKAGESDIR="$TMP/packages"
TMP_REQUIREMENTS="$TMP/requirements.txt"
TMP_PIP_FREEZE="$TMP/pip-freeze.txt"
trap 'rc=$?; rm -rf "$TMP"; exit $rc' EXIT

sed -n 's/ *#.*//; s/\[[^]]*\]//g; s/^pip==.*/pip/; /./p' ./requirements.txt | sort >"$TMP_REQUIREMENTS"

pip install --target="$TMP_PACKAGESDIR" -r ./requirements.txt
pip freeze --path="$TMP_PACKAGESDIR" --all | sed 's/^pip==.*/pip/' | sort >"$TMP_PIP_FREEZE"

if ! diff -u "$TMP_REQUIREMENTS" "$TMP_PIP_FREEZE"; then
  echo >&2 "requirements.txt doesn't have all dependencies pinned. Please check output above to see what should be added."
  exit 1
fi
