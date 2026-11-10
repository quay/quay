#!/usr/bin/env bash
#
# Pre-commit hook: GHA installs @playwright/test from web/pnpm-lock.yaml, while
# Prow runs `npm ci` from, and web/Containerfile.playwright pins its Playwright
# to, web/package-lock.json.
# Fail when the two lockfiles resolve different Playwright versions.
#
set -euo pipefail

PNPM_LOCK="web/pnpm-lock.yaml"
NPM_LOCK="web/package-lock.json"

pnpm_version=$(awk '
  /^[^ ]/ { importers = ($0 == "importers:") }
  importers && /^  [^ ]/ { root = ($0 == "  .:") }
  root && /^    [^ ]/ { dev = ($0 == "    devDependencies:") }
  dev && $0 == "      '\''@playwright/test'\'':" { found = 1; next }
  found && /^        version:/ { print $2; exit }
  found && /^      [^ ]/ { exit }
' "$PNPM_LOCK")

npm_version=$(node -p "require('./$NPM_LOCK').packages['node_modules/@playwright/test']?.version ?? ''")

if [[ -z "$pnpm_version" || "$pnpm_version" != "$npm_version" ]]; then
  echo "check-playwright-lock: @playwright/test is ${pnpm_version:-missing} in $PNPM_LOCK but ${npm_version:-missing} in $NPM_LOCK"
  exit 1
fi
