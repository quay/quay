#!/bin/bash
# workflow-next-step.sh -- Stop hook that suggests the next workflow step.
#
# Checks git state and open PRs to nudge toward /pr, /poll, or /backport.
# Outputs JSON with systemMessage for the user.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
BRANCH=$(git branch --show-current 2>/dev/null || true)

[ -z "$BRANCH" ] && exit 0
[ "$BRANCH" = "master" ] && exit 0

msg=""

# Check for uncommitted changes
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  msg="You have uncommitted changes on ${BRANCH}."
  echo "{\"systemMessage\": \"${msg}\"}"
  exit 0
fi

# Check for unpushed commits
UNPUSHED=$(git log "origin/${BRANCH}..HEAD" --oneline 2>/dev/null | head -1)
if [ -n "$UNPUSHED" ]; then
  msg="You have unpushed commits on ${BRANCH}. Consider running /pr to open a pull request."
  echo "{\"systemMessage\": \"${msg}\"}"
  exit 0
fi

# Check if branch has an open PR
if command -v gh &>/dev/null; then
  PR_JSON=$(gh pr list --head "$BRANCH" --repo quay/quay --json number,state --jq '.[0]' 2>/dev/null || true)
  PR_NUM=$(echo "$PR_JSON" | jq -r '.number // empty' 2>/dev/null || true)

  if [ -n "$PR_NUM" ]; then
    POLL_STATE="${REPO_ROOT}/.claude/poll-state/pr-${PR_NUM}.json"
    if [ -f "$POLL_STATE" ]; then
      LAST_EXIT=$(jq -r '.last_exit_code // empty' "$POLL_STATE" 2>/dev/null || true)
      case "$LAST_EXIT" in
        1) msg="PR #${PR_NUM} has CI failures. Fix the issues and re-run /poll ${PR_NUM}." ;;
        3) msg="PR #${PR_NUM} has review comments to address. Fix and re-run /poll ${PR_NUM}." ;;
        4) msg="PR #${PR_NUM} is awaiting human review." ;;
        0) msg="PR #${PR_NUM} CI is green — check if it's ready to merge." ;;
      esac
    else
      msg="PR #${PR_NUM} is open. Run /poll ${PR_NUM} to monitor CI and reviews."
    fi

    if [ -n "$msg" ]; then
      echo "{\"systemMessage\": \"${msg}\"}"
      exit 0
    fi
  fi
fi

exit 0
