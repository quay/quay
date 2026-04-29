#!/bin/bash
# save-session-state.sh -- PreCompact hook that persists workflow state.
#
# Saves current branch, JIRA ticket, and PR number so context survives compaction.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
STATE_DIR="${REPO_ROOT}/.claude/session-state"
STATE_FILE="${STATE_DIR}/current.json"
mkdir -p "$STATE_DIR"

BRANCH=$(git branch --show-current 2>/dev/null || true)
TICKET=$(echo "$BRANCH" | grep -oiP '(PROJQUAY|QUAYIO)-\d+' | head -1 || true)

PR_NUM=""
if command -v gh &>/dev/null && [ -n "$BRANCH" ] && [ "$BRANCH" != "master" ]; then
  PR_NUM=$(gh pr list --head "$BRANCH" --repo quay/quay --json number --jq '.[0].number' 2>/dev/null || true)
fi

SAVED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
jq -n \
  --arg branch "$BRANCH" \
  --arg ticket "$TICKET" \
  --arg pr_number "$PR_NUM" \
  --arg saved_at "$SAVED_AT" \
  '{branch:$branch,ticket:$ticket,pr_number:$pr_number,saved_at:$saved_at}' > "$STATE_FILE"

CONTEXT="Session state saved before compaction. Branch: ${BRANCH:-master}"
[ -n "$TICKET" ] && CONTEXT="${CONTEXT}, Ticket: ${TICKET}"
[ -n "$PR_NUM" ] && CONTEXT="${CONTEXT}, PR: #${PR_NUM}"

jq -n --arg ctx "$CONTEXT" \
  '{hookSpecificOutput:{hookEventName:"PreCompact",additionalContext:$ctx}}'
