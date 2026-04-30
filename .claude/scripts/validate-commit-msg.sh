#!/bin/bash
# validate-commit-msg.sh -- PreToolUse hook for git commit.
# Reads tool_input JSON from stdin, extracts the commit message,
# and blocks if it doesn't match: <subsystem>: <what changed>
#
# Handles -m 'msg', -m "msg", and HEREDOC-style -m "$(cat <<'EOF'...EOF)"

set -euo pipefail

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$CMD" ]; then
  exit 0
fi

# Skip --amend with no -m (reuses previous message)
if echo "$CMD" | grep -q -- '--amend' && ! echo "$CMD" | grep -q -- ' -m '; then
  exit 0
fi

MSG=""

# Strategy 1: HEREDOC -m "$(cat <<'EOF' ... EOF )" — check first to avoid
# the double-quote strategy grabbing "$(cat <<'EOF'" as the message
if [ -z "$MSG" ]; then
  MSG=$(echo "$CMD" | sed -n "/<<'EOF'/,/^EOF$/p" 2>/dev/null | sed '1d;$d' | head -1 || true)
fi
if [ -z "$MSG" ]; then
  MSG=$(echo "$CMD" | sed -n '/<<EOF/,/^EOF$/p' 2>/dev/null | sed '1d;$d' | head -1 || true)
fi

# Strategy 2: simple -m 'message'
if [ -z "$MSG" ]; then
  MSG=$(echo "$CMD" | grep -oP -- "-m \x27\K[^\x27]+" 2>/dev/null | head -1 || true)
fi

# Strategy 3: simple -m "message" (only if no command substitution)
if [ -z "$MSG" ]; then
  CANDIDATE=$(echo "$CMD" | grep -oP -- '-m "\K[^"]+' 2>/dev/null | head -1 || true)
  if [ -n "$CANDIDATE" ] && ! echo "$CANDIDATE" | grep -q '^\$'; then
    MSG="$CANDIDATE"
  fi
fi

# If the command explicitly supplies a message, failing to extract it should block.
if [ -z "$MSG" ]; then
  if echo "$CMD" | grep -qE -- '(^|[[:space:]])(--message(=|[[:space:]])|-m([[:space:]]|$)|-F([[:space:]]|$)|--file(=|[[:space:]]))'; then
    echo "BLOCKED: Could not parse the commit message for validation." >&2
    exit 2
  fi
  exit 0
fi

FIRST_LINE=$(echo "$MSG" | head -1)

# Validate: <subsystem>: <what changed>
if ! echo "$FIRST_LINE" | grep -qE '^[[:alnum:]_/.-]+: .+'; then
  echo "BLOCKED: Commit message does not match required format." >&2
  echo "Expected: <subsystem>: <what changed> (PROJQUAY-####|NO-ISSUE)" >&2
  echo "Got: $FIRST_LINE" >&2
  exit 2
fi
