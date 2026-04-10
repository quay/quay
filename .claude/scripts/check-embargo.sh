#!/bin/bash
# check-embargo.sh - Block Claude from processing embargoed JIRA tickets
#
# Claude Code hook for UserPromptSubmit and PreToolUse events.
# Checks the "Embargo Status" field (customfield_10860) on referenced tickets.
#
# Exit 0 = allow, Exit 2 = block (with reason on stderr)

set -o pipefail

ACLI="${ACLI_PATH:-acli}"

# Fail open if acli not available
if ! command -v "$ACLI" &>/dev/null; then
  exit 0
fi

INPUT=$(cat)
HOOK_EVENT=$(echo "$INPUT" | jq -r '.hook_event_name // empty')

# Determine what text to scan for JIRA keys
case "$HOOK_EVENT" in
  PreToolUse)
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
    [ "$TOOL_NAME" != "Bash" ] && exit 0
    TEXT=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
    # Only check commands that interact with JIRA
    echo "$TEXT" | grep -qi 'jira' || exit 0
    ;;
  UserPromptSubmit)
    TEXT=$(echo "$INPUT" | jq -r '.prompt // empty')
    ;;
  *)
    exit 0
    ;;
esac

[ -z "$TEXT" ] && exit 0

# Extract unique JIRA ticket keys
KEYS=$(echo "$TEXT" | grep -oE '[A-Z][A-Z0-9]+-[0-9]+' | sort -u)
[ -z "$KEYS" ] && exit 0

# Check each ticket's Embargo Status (customfield_10860)
BLOCKED=""
while IFS= read -r KEY; do
  RESULT=$(timeout 10 "$ACLI" jira workitem view "$KEY" --fields 'customfield_10860' --json 2>/dev/null) || continue
  EMBARGO_VAL=$(echo "$RESULT" | jq -r '.fields.customfield_10860.value // empty')
  if [ "$EMBARGO_VAL" = "True" ]; then
    BLOCKED="${BLOCKED}  - ${KEY}\n"
  fi
done <<< "$KEYS"

if [ -n "$BLOCKED" ]; then
  cat >&2 <<EOF
BLOCKED: Embargoed JIRA ticket(s) detected.
Embargoed tickets must not be processed by AI assistants.

Embargoed tickets:
$(echo -e "$BLOCKED")
Remove these ticket references from your prompt to proceed.
If the embargo has been lifted, update the ticket's Embargo Status in JIRA first.
EOF
  exit 2
fi

exit 0
