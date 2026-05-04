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

# Use python3 shlex to correctly parse shell argv — portable and handles all
# quoting/escaping forms. CMD is passed as argv[1] to avoid stdin conflict.
TITLE=$(python3 -c '
import shlex, sys

cmd = sys.argv[1] if len(sys.argv) > 1 else ""
try:
    argv = shlex.split(cmd, posix=True)
except ValueError:
    sys.exit(0)

title = ""
for i, arg in enumerate(argv):
    if arg == "--title" and i + 1 < len(argv):
        title = argv[i + 1]
        break
    if arg.startswith("--title="):
        title = arg.split("=", 1)[1]
        break

print(title, end="")
' "$CMD")

# No --title flag found -- nothing to validate
if [ -z "$TITLE" ]; then
  exit 0
fi

PATTERN='^(\[redhat-[0-9]+\.[0-9]+\] )?(PROJQUAY-[0-9]+|QUAYIO-[0-9]+|NO-ISSUE): [a-z]+(\([^)]+\))?: .+$'

if ! echo "$TITLE" | grep -qE "$PATTERN"; then
  echo "BLOCKED: PR title does not match required format." >&2
  echo "Expected: [redhat-X.Y] (PROJQUAY-XXXX|QUAYIO-XXXX|NO-ISSUE): type(scope): description" >&2
  echo "Got: $TITLE" >&2
  exit 2
fi
