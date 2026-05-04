#!/bin/bash
# format-and-lint.sh -- Run pre-commit hooks for the Quay project.
#
# Usage:
#   bash scripts/format-and-lint.sh              # Run on staged files (default)
#   bash scripts/format-and-lint.sh --all-files  # Run on all files
#   bash scripts/format-and-lint.sh <hook-id>    # Run a specific hook
#
# Wraps the project's .pre-commit-config.yaml which includes:
#   gitleaks, black, isort, config-files-check, no-new-cypress-tests,
#   requirements-build-sync, eslint, trailing-whitespace, end-of-file-fixer

set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
ARGS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --all-files)
      ARGS+=(--all-files)
      shift
      ;;
    --hook)
      [ $# -ge 2 ] || {
        echo "Usage: $0 [--all-files] [--hook <id>]" >&2
        exit 1
      }
      ARGS+=("$2")
      shift 2
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

# ── Ensure pre-commit is installed ────────────────────────────────
if ! command -v pre-commit &>/dev/null; then
  echo "pre-commit not found. Installing..."
  pip install pre-commit 2>&1 | tail -3
fi

# ── Ensure hooks are installed in this repo ───────────────────────
if [ ! -f "$REPO_ROOT/.git/hooks/pre-commit" ] || ! grep -q "pre-commit" "$REPO_ROOT/.git/hooks/pre-commit" 2>/dev/null; then
  echo "Installing pre-commit hooks..."
  cd "$REPO_ROOT" && pre-commit install 2>&1 | tail -2
fi

# ── Run pre-commit ────────────────────────────────────────────────
echo "============================================"
echo "  Quay Pre-commit Checks"
echo "============================================"
echo ""

cd "$REPO_ROOT"

if pre-commit run "${ARGS[@]}" 2>&1; then
  echo ""
  echo "============================================"
  echo "  RESULT: All pre-commit hooks passed"
  echo "============================================"
else
  EXIT_CODE=$?
  echo ""
  echo "============================================"
  echo "  RESULT: Pre-commit hooks found issues"
  echo "  (some may have been auto-fixed -- check git diff)"
  echo "============================================"
  exit $EXIT_CODE
fi
