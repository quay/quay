#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
WEB_DIR="${REPO_ROOT}/web"

# 1. Resolve web/node_modules if missing
if [ ! -d "${WEB_DIR}/node_modules" ]; then
  COMMON_DIR="$(git rev-parse --git-common-dir 2>/dev/null || true)"
  if [ -n "${COMMON_DIR}" ]; then
    MAIN_REPO="$(cd "${COMMON_DIR}/.." && pwd -P)"
    if [ "${MAIN_REPO}" != "${REPO_ROOT}" ] && [ -d "${MAIN_REPO}/web/node_modules" ]; then
      echo "Linking web/node_modules from main repository checkout (${MAIN_REPO})..."
      ln -sfn "${MAIN_REPO}/web/node_modules" "${WEB_DIR}/node_modules"
    fi
  fi
fi

if [ ! -d "${WEB_DIR}/node_modules" ]; then
  if command -v pnpm &>/dev/null; then
    echo "web/node_modules not found; installing dependencies via pnpm..."
    (cd "${WEB_DIR}" && pnpm install --frozen-lockfile --prefer-offline --silent)
  elif command -v corepack &>/dev/null; then
    echo "web/node_modules not found; installing dependencies via corepack pnpm..."
    (cd "${WEB_DIR}" && corepack pnpm install --frozen-lockfile --prefer-offline --silent)
  elif command -v npx &>/dev/null; then
    echo "web/node_modules not found; installing dependencies via npx pnpm..."
    (cd "${WEB_DIR}" && npx --yes pnpm install --frozen-lockfile --prefer-offline --silent)
  fi
fi

# 2. Run Playwright required usage tags check if typescript is available
if [ -d "${WEB_DIR}/node_modules/typescript" ]; then
  exec node "${WEB_DIR}/playwright/ensure-required-tags.cjs" "$@"
fi

# 3. Fallback when dependencies cannot be resolved
if [ "${CI:-false}" = "true" ] || [ "${PRE_COMMIT_STRICT:-false}" = "true" ]; then
  echo "::error::typescript dependency not found for ensure-required-tags.cjs. Run 'cd web && pnpm install'." >&2
  exit 1
else
  echo "Warning: web/node_modules not found; skipping Playwright tag check. (Run 'cd web && pnpm install' to enable)" >&2
  exit 0
fi
