#!/usr/bin/env bash
#
# Pre-commit hook: verify every node_modules/ entry in web/package-lock.json
# has a "resolved" URL.  This is a defense-in-depth measure -- the .npmrc
# setting prevents stripping, but this hook catches it if someone bypasses
# .npmrc.
#
set -euo pipefail

LOCKFILE="web/package-lock.json"

if [[ ! -f "$LOCKFILE" ]]; then
  echo "check-lockfile-resolved: ERROR — $LOCKFILE not found."
  exit 1
fi

missing=$(node -e '
  const pkg = require("./" + process.argv[1]);
  const entries = Object.entries(pkg.packages || {})
    .filter(([k]) => k.startsWith("node_modules/"));
  const missing = entries.filter(([, v]) => !v.resolved);
  if (missing.length > 0) {
    console.log("ERROR: " + missing.length + " package(s) in " + process.argv[1] +
      " are missing \"resolved\" URLs:");
    missing.forEach(([k]) => console.log("  - " + k));
    process.exit(1);
  } else {
    console.log("check-lockfile-resolved: all " + entries.length +
      " packages have resolved URLs.");
  }
' "$LOCKFILE") || {
  echo "$missing"
  echo ""
  echo "To fix, run in the web/ directory:"
  echo "  npm install --package-lock-only --legacy-peer-deps"
  echo ""
  echo "If the problem persists, check that web/.npmrc contains:"
  echo "  omit-lockfile-registry-resolved=false"
  exit 1
}

echo "$missing"
exit 0
