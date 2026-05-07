#!/bin/bash
# coderabbit-review-gate.sh -- PreToolUse hook for gh pr create.
# Runs CodeRabbit AI review before PR creation and blocks on error-level findings.
#
# Exit codes:
#   0 = pass (or non-matching command, or graceful skip)
#   2 = blocked — CodeRabbit found error-level issues

set -uo pipefail

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$CMD" ]; then
  exit 0
fi

if ! echo "$CMD" | grep -q 'gh pr create'; then
  exit 0
fi

if ! command -v coderabbit &>/dev/null; then
  echo "[coderabbit-review-gate] CodeRabbit CLI not found — skipping review gate" >&2
  exit 0
fi

if [ -z "${CODERABBIT_API_KEY:-}" ]; then
  echo "[coderabbit-review-gate] CODERABBIT_API_KEY not set — skipping review gate" >&2
  echo "[coderabbit-review-gate] Connect your key in ACP Integrations or run: coderabbit auth login" >&2
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
BASE_BRANCH="master"

CHANGED_FILES=$(git diff "$BASE_BRANCH"...HEAD --name-only 2>/dev/null || git diff HEAD~1 --name-only 2>/dev/null || true)
if [ -z "$CHANGED_FILES" ]; then
  echo "[coderabbit-review-gate] No changed files — skipping review" >&2
  exit 0
fi

echo "[coderabbit-review-gate] Running CodeRabbit review before PR creation..." >&2

CR_OUTPUT=$(cd "$REPO_ROOT" && coderabbit review --agent --base "$BASE_BRANCH" 2>&1 || true)

CR_JSON=$(echo "$CR_OUTPUT" | jq -c '.' 2>/dev/null || true)

CR_ERROR_TYPE=$(echo "$CR_JSON" | jq -r 'select(.type == "error") | .errorType' 2>/dev/null | head -1 || true)

if [ "$CR_ERROR_TYPE" = "rate_limit" ]; then
  echo "[coderabbit-review-gate] Rate-limited — allowing PR creation" >&2
  exit 0
fi

if [ "$CR_ERROR_TYPE" = "auth" ]; then
  echo "[coderabbit-review-gate] Auth failed — allowing PR creation" >&2
  exit 0
fi

if [ -n "$CR_JSON" ]; then
  BLOCKING=$(echo "$CR_JSON" | jq -r \
    'select(.type == "finding" or .findings != null) |
     (.findings[]? // .) | select(.severity == "error") |
     "  \(.file):\(.line) — \(.message)"' \
    2>/dev/null || true)

  if [ -n "$BLOCKING" ]; then
    echo "" >&2
    echo "=================================================" >&2
    echo "BLOCKED: CodeRabbit found error-level issues" >&2
    echo "=================================================" >&2
    echo "$BLOCKING" >&2
    echo "" >&2
    echo "Fix these issues and retry gh pr create." >&2
    exit 2
  fi
fi

echo "[coderabbit-review-gate] CodeRabbit review passed" >&2
exit 0
