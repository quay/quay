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
  if command -v npm &>/dev/null; then
    echo "web/node_modules not found; installing dependencies via npm..."
    (cd "${WEB_DIR}" && npm ci --silent)
  fi
fi

# 2. Run ESLint if available
if [ -x "${WEB_DIR}/node_modules/.bin/eslint" ]; then
  exec "${WEB_DIR}/node_modules/.bin/eslint" --fix "$@"
fi

# 3. Fallback when dependencies cannot be resolved
if [ "${CI:-false}" = "true" ] || [ "${PRE_COMMIT_STRICT:-false}" = "true" ]; then
  echo "::error::web/node_modules/.bin/eslint not found. Run 'cd web && npm ci'." >&2
  exit 1
else
  echo "Warning: web/node_modules not found; skipping web ESLint. (Run 'cd web && npm ci' to enable)" >&2
  exit 0
fi
