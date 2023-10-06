#!/bin/sh -eu
TMP=$(mktemp -d "${TMPDIR:-/tmp/}quay-verify-requirements.XXXXXXXX")
TMP_PACKAGESDIR="$TMP/packages"
TMP_REQUIREMENTS="$TMP/requirements.txt"
TMP_CONSTRAINTS="$TMP/constraints.txt"
TMP_REQUIREMENTS_FULL="$TMP/requirements-full.txt"
TMP_PIP_FREEZE="$TMP/pip-freeze.txt"
trap 'rc=$?; rm -rf "$TMP"; exit $rc' EXIT

sed '/^# Indirect dependencies/,$d' ./requirements.txt | sort >"$TMP_REQUIREMENTS"
sed -n '/^# Indirect dependencies/,$p' ./requirements.txt | sort >"$TMP_CONSTRAINTS"
sed -n 's/ *#.*//; s/\[[^]]*\]//g; /./p' ./requirements.txt | sort >"$TMP_REQUIREMENTS_FULL"

pip install --target="$TMP_PACKAGESDIR" -r "$TMP_REQUIREMENTS" -c "$TMP_CONSTRAINTS"
pip freeze --path="$TMP_PACKAGESDIR" --all | sort >"$TMP_PIP_FREEZE"

if ! diff -u "$TMP_REQUIREMENTS_FULL" "$TMP_PIP_FREEZE"; then
  echo >&2 "requirements.txt doesn't have all dependencies pinned correctly. Please check output above to see what should be added or removed."
  exit 1
fi
