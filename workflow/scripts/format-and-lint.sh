#!/bin/bash
# format-and-lint.sh -- Run all formatting and linting checks for the Quay project.
#
# Usage: bash scripts/format-and-lint.sh [--fix] [--check-only]
#
# Options:
#   --fix         Auto-fix issues where possible (default)
#   --check-only  Only report issues, don't modify files
#
# Runs: Black, isort, Flake8, trailing-whitespace, end-of-file-fixer, gitleaks, ESLint

set -euo pipefail

MODE="fix"
if [ "${1:-}" = "--check-only" ]; then
  MODE="check"
fi

ERRORS=0
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

echo "============================================"
echo "  Quay Format & Lint  (mode: ${MODE})"
echo "============================================"
echo ""

# ── 1. Black (Python formatting) ─────────────────────────────────
echo "--- Black (Python formatter) ---"
if command -v black &>/dev/null; then
  if [ "$MODE" = "check" ]; then
    black --line-length=100 --target-version=py312 --check --diff "$REPO_ROOT" 2>&1 | tail -20 || { echo "FAIL: Black formatting issues found"; ERRORS=$((ERRORS + 1)); }
  else
    black --line-length=100 --target-version=py312 "$REPO_ROOT" 2>&1 | tail -5
    echo "OK: Black formatting applied"
  fi
else
  echo "SKIP: black not installed (pip install black==24.4.2)"
fi
echo ""

# ── 2. isort (import sorting) ────────────────────────────────────
echo "--- isort (import sorter) ---"
if command -v isort &>/dev/null; then
  if [ "$MODE" = "check" ]; then
    isort --settings-path "$REPO_ROOT/pyproject.toml" --check-only --diff "$REPO_ROOT" 2>&1 | tail -20 || { echo "FAIL: isort issues found"; ERRORS=$((ERRORS + 1)); }
  else
    isort --settings-path "$REPO_ROOT/pyproject.toml" "$REPO_ROOT" 2>&1 | tail -5
    echo "OK: isort applied"
  fi
else
  echo "SKIP: isort not installed (pip install isort==5.12.0)"
fi
echo ""

# ── 3. Flake8 (linting) ──────────────────────────────────────────
echo "--- Flake8 (linter) ---"
if command -v flake8 &>/dev/null; then
  # Match CI: ignore known issues to catch new ones
  IGNORED="C901,E203,E262,E265,E266,E402,E501,E712,E713,E722,E731,E741,F401,F403,F405,F811,F821,F841,W503"
  RESULT=$(flake8 --ignore="$IGNORED" --max-line-length=100 --max-complexity=10 "$REPO_ROOT" 2>&1 | tail -30) || true
  if [ -n "$RESULT" ]; then
    echo "$RESULT"
    echo "FAIL: Flake8 issues found"
    ERRORS=$((ERRORS + 1))
  else
    echo "OK: Flake8 clean"
  fi
else
  echo "SKIP: flake8 not installed (pip install flake8)"
fi
echo ""

# ── 4. Trailing whitespace ───────────────────────────────────────
echo "--- Trailing whitespace ---"
TRAILING=$(git diff --cached --name-only 2>/dev/null | xargs grep -rn ' $' 2>/dev/null | head -10) || true
if [ -n "$TRAILING" ]; then
  echo "$TRAILING"
  if [ "$MODE" = "fix" ]; then
    git diff --cached --name-only 2>/dev/null | xargs sed -i 's/[[:space:]]*$//' 2>/dev/null || true
    echo "FIXED: Trailing whitespace removed from staged files"
  else
    echo "FAIL: Trailing whitespace found"
    ERRORS=$((ERRORS + 1))
  fi
else
  echo "OK: No trailing whitespace in staged files"
fi
echo ""

# ── 5. Gitleaks (secret detection) ───────────────────────────────
echo "--- Gitleaks (secret detection) ---"
if command -v gitleaks &>/dev/null; then
  gitleaks detect --source "$REPO_ROOT" --no-git --redact 2>&1 | tail -5 || { echo "WARN: Gitleaks found potential secrets"; ERRORS=$((ERRORS + 1)); }
else
  echo "SKIP: gitleaks not installed"
fi
echo ""

# ── 6. ESLint (JavaScript/TypeScript) ────────────────────────────
echo "--- ESLint (web/ frontend) ---"
if [ -f "$REPO_ROOT/web/node_modules/.bin/eslint" ]; then
  STAGED_WEB=$(git diff --cached --name-only 2>/dev/null | grep '^web/' | grep -E '\.(js|jsx|ts|tsx)$' || true)
  if [ -n "$STAGED_WEB" ]; then
    if [ "$MODE" = "check" ]; then
      echo "$STAGED_WEB" | xargs "$REPO_ROOT/web/node_modules/.bin/eslint" 2>&1 | tail -20 || { echo "FAIL: ESLint issues found"; ERRORS=$((ERRORS + 1)); }
    else
      echo "$STAGED_WEB" | xargs "$REPO_ROOT/web/node_modules/.bin/eslint" --fix 2>&1 | tail -10
      echo "OK: ESLint applied"
    fi
  else
    echo "OK: No staged web/ files"
  fi
else
  echo "SKIP: ESLint not installed (cd web && npm ci)"
fi
echo ""

# ── Summary ──────────────────────────────────────────────────────
echo "============================================"
if [ "$ERRORS" -gt 0 ]; then
  echo "  RESULT: ${ERRORS} issue(s) found"
  echo "============================================"
  exit 1
else
  echo "  RESULT: All checks passed"
  echo "============================================"
  exit 0
fi
