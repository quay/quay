#!/bin/bash
# validate-pr-title.sh -- PreToolUse hook for gh pr create.
# Reads tool_input JSON from stdin, extracts the PR title from --title flag,
# and blocks if it does not match the CI-enforced regex:
#   ^(\[redhat-[0-9]+\.[0-9]+\] )?(PROJQUAY-[0-9]+|QUAYIO-[0-9]+|NO-ISSUE): [a-z]+(\([^)]+\))?: .+$

set -euo pipefail

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$CMD" ]; then
  exit 0
fi

TITLE=""

# Strategy 1: --title 'message' (single quotes)
if [ -z "$TITLE" ]; then
  TITLE=$(echo "$CMD" | grep -oP -- "--title[= ]\x27\K[^\x27]+" 2>/dev/null | head -1 || true)
fi

# Strategy 2: --title "message" (double quotes)
if [ -z "$TITLE" ]; then
  TITLE=$(echo "$CMD" | grep -oP -- '--title[= ]"\K[^"]+' 2>/dev/null | head -1 || true)
fi

# Strategy 3: --title=bare-value (no quotes, stop at space)
if [ -z "$TITLE" ]; then
  TITLE=$(echo "$CMD" | grep -oP -- "--title=\K[^ \x27\"]+" 2>/dev/null | head -1 || true)
fi

# No --title flag found -- nothing to validate
if [ -z "$TITLE" ]; then
  exit 0
fi

PATTERN='^(\[redhat-[0-9]+\.[0-9]+\] )?(PROJQUAY-[0-9]+|QUAYIO-[0-9]+|NO-ISSUE): [a-z]+(\([^)]+\))?: .+$'

if ! echo "$TITLE" | grep -qE "$PATTERN"; then
  echo "BLOCKED: PR title does not match required format." >&2
  echo "Expected: PROJQUAY-XXXX: type(scope): description" >&2
  echo "Got: $TITLE" >&2
  exit 2
fi
