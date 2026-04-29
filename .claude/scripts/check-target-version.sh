#!/bin/bash
# check-target-version.sh -- PostToolUse hook after git push.
#
# Warns if the JIRA ticket doesn't have Target Version set,
# since the merge bot will block without it.

ACLI="${ACLI_PATH:-acli}"

BRANCH=$(git branch --show-current 2>/dev/null || true)
[ -z "$BRANCH" ] && exit 0
[ "$BRANCH" = "master" ] && exit 0

TICKET=$(echo "$BRANCH" | grep -oiP '(PROJQUAY|QUAYIO)-\d+' | head -1 || true)
[ -z "$TICKET" ] && exit 0

TARGET_VERSION=""
if command -v "$ACLI" &>/dev/null; then
  RESULT=$(timeout 10 "$ACLI" jira workitem view "$TICKET" --fields 'customfield_10855' --json 2>/dev/null) || true
  TARGET_VERSION=$(echo "$RESULT" | jq -r '.fields.customfield_10855[0].name // empty' 2>/dev/null || true)
elif [ -n "${JIRA_API_TOKEN:-}" ] && [ -n "${JIRA_USER:-}" ]; then
  RESULT=$(curl -s -u "${JIRA_USER}:${JIRA_API_TOKEN}" \
    "https://redhat.atlassian.net/rest/api/2/issue/${TICKET}?fields=customfield_10855" 2>/dev/null) || true
  TARGET_VERSION=$(echo "$RESULT" | jq -r '.fields.customfield_10855[0].name // empty' 2>/dev/null || true)
fi

if [ -z "$TARGET_VERSION" ]; then
  jq -n --arg ticket "$TICKET" \
    '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:("Warning: " + $ticket + " has no Target Version set. The merge bot will block this PR. Run /jira " + $ticket + " set-version to fix.")}}'
fi

exit 0
