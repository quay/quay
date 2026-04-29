#!/bin/bash
# detect-jira-ticket.sh -- UserPromptSubmit hook that detects JIRA references.
#
# If the user mentions PROJQUAY-XXXX or QUAYIO-XXXX without using /jira or /start,
# injects a hint about available commands.

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)
[ -z "$PROMPT" ] && exit 0

# Skip if user is already invoking a JIRA-aware skill
echo "$PROMPT" | grep -qP '^\s*/(jira|start|backport|implement-story|create-plan|estimate-issue|create-epic|create-stories)\s' && exit 0

TICKETS=$(echo "$PROMPT" | grep -oP '(PROJQUAY|QUAYIO)-\d+' | sort -u | head -5)
[ -z "$TICKETS" ] && exit 0

TICKET_LIST=$(echo "$TICKETS" | tr '\n' ', ' | sed 's/,$//')

echo "{\"hookSpecificOutput\": {\"hookEventName\": \"UserPromptSubmit\", \"additionalContext\": \"Detected JIRA reference(s): ${TICKET_LIST}. Use /jira <ticket> to view details or /start <ticket> to begin work on a ticket.\"}}"
