#!/bin/bash
# poll-pr.sh -- Poll a PR for CodeRabbit feedback, GitHub Actions results,
#               Codecov reports, and human review status.
#
# Usage: bash scripts/poll-pr.sh <PR_NUMBER> [--repo owner/repo] [--wait]
#
# Options:
#   --repo    Override repository (default: quay/quay)
#   --wait    Keep polling every 60s until all checks pass or fail
#
# Outputs a structured report of PR status for the agent to act on.

set -euo pipefail

PR_NUMBER="${1:?Usage: poll-pr.sh <PR_NUMBER> [--repo owner/repo] [--wait]}"
shift

REPO="quay/quay"
WAIT=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --wait) WAIT=true; shift ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

poll_once() {
  echo "============================================================"
  echo "  PR #${PR_NUMBER} Status Report  ($(date '+%Y-%m-%d %H:%M:%S'))"
  echo "============================================================"
  echo ""

  # ── 1. PR metadata ──────────────────────────────────────────────
  echo "--- PR Details ---"
  gh pr view "$PR_NUMBER" --repo "$REPO" \
    --json title,state,isDraft,mergeable,labels,reviewDecision \
    --jq '{
      title: .title,
      state: .state,
      draft: .isDraft,
      mergeable: .mergeable,
      review_decision: .reviewDecision,
      labels: [.labels[].name] | join(", ")
    }' 2>/dev/null || echo "(could not fetch PR metadata)"
  echo ""

  # ── 2. GitHub Actions / Check Runs ──────────────────────────────
  echo "--- CI Check Runs ---"
  gh pr checks "$PR_NUMBER" --repo "$REPO" 2>/dev/null || echo "(no checks found)"
  echo ""

  # ── 3. CodeRabbit Review ────────────────────────────────────────
  echo "--- CodeRabbit Review ---"
  CODERABBIT_REVIEW=$(gh api "repos/${REPO}/pulls/${PR_NUMBER}/reviews" \
    --jq '[.[] | select(.user.login == "coderabbitai[bot]")] | last' 2>/dev/null || echo "")

  if [ -n "$CODERABBIT_REVIEW" ] && [ "$CODERABBIT_REVIEW" != "null" ]; then
    echo "$CODERABBIT_REVIEW" | jq -r '{
      state: .state,
      submitted_at: .submitted_at,
      body_preview: (.body | split("\n") | .[0:5] | join("\n"))
    }' 2>/dev/null || echo "(could not parse CodeRabbit review)"
  else
    echo "(no CodeRabbit review yet)"
  fi
  echo ""

  # ── 4. CodeRabbit Comments (actionable feedback) ────────────────
  echo "--- CodeRabbit Comments ---"
  CODERABBIT_COMMENTS=$(gh api "repos/${REPO}/pulls/${PR_NUMBER}/comments" \
    --jq '[.[] | select(.user.login == "coderabbitai[bot]")] | length' 2>/dev/null || echo "0")
  echo "CodeRabbit inline comments: ${CODERABBIT_COMMENTS}"

  if [ "$CODERABBIT_COMMENTS" -gt 0 ] 2>/dev/null; then
    echo ""
    echo "Latest CodeRabbit comments:"
    gh api "repos/${REPO}/pulls/${PR_NUMBER}/comments" \
      --jq '[.[] | select(.user.login == "coderabbitai[bot]")] | .[-3:] | .[] | "  File: \(.path):\(.line // .original_line // "?")\n  \(.body | split("\n") | .[0:3] | join("\n  "))\n"' 2>/dev/null || true
  fi
  echo ""

  # ── 5. CodeRabbit PR-level comment (walkthrough + pre-merge checks) ─
  echo "--- CodeRabbit Walkthrough & Pre-merge Checks ---"
  WALKTHROUGH=$(gh api "repos/${REPO}/issues/${PR_NUMBER}/comments" \
    --jq '[.[] | select(.user.login == "coderabbitai[bot]")] | last | .body' 2>/dev/null || echo "")

  if [ -n "$WALKTHROUGH" ] && [ "$WALKTHROUGH" != "null" ]; then
    # Extract pre-merge check results
    echo "$WALKTHROUGH" | grep -A 2 -E "(pass|fail|warn|✅|❌|⚠️)" | head -30 || true
    echo ""
    # Extract any actionable items
    echo "Actionable items from walkthrough:"
    echo "$WALKTHROUGH" | grep -E "(TODO|FIXME|suggest|consider|should|must|warning|error)" -i | head -10 || echo "  (none found)"
  else
    echo "(no walkthrough comment yet)"
  fi
  echo ""

  # ── 6. Codecov Report ───────────────────────────────────────────
  echo "--- Codecov Report ---"
  CODECOV_COMMENT=$(gh api "repos/${REPO}/issues/${PR_NUMBER}/comments" \
    --jq '[.[] | select(.user.login == "codecov[bot]")] | last | .body' 2>/dev/null || echo "")

  if [ -n "$CODECOV_COMMENT" ] && [ "$CODECOV_COMMENT" != "null" ]; then
    echo "$CODECOV_COMMENT" | grep -E "(Coverage|coverage|Diff|diff|patch|project)" | head -10 || echo "  (coverage data present but could not extract summary)"
  else
    echo "(no Codecov report yet)"
  fi
  echo ""

  # ── 7. Human Reviews ───────────────────────────────────────────
  echo "--- Human Reviews ---"
  gh api "repos/${REPO}/pulls/${PR_NUMBER}/reviews" \
    --jq '[.[] | select(.user.login != "coderabbitai[bot]" and .user.login != "github-actions[bot]")] | .[] | "\(.user.login): \(.state) (\(.submitted_at))"' 2>/dev/null || echo "(no human reviews yet)"
  echo ""

  # ── 8. JIRA Bot Status ─────────────────────────────────────────
  echo "--- JIRA Bot (openshift-ci-robot) ---"
  JIRA_COMMENT=$(gh api "repos/${REPO}/issues/${PR_NUMBER}/comments" \
    --jq '[.[] | select(.user.login == "openshift-ci[bot]" or .user.login == "openshift-ci-robot")] | last | .body' 2>/dev/null || echo "")

  if [ -n "$JIRA_COMMENT" ] && [ "$JIRA_COMMENT" != "null" ]; then
    echo "$JIRA_COMMENT" | head -15
  else
    echo "(no JIRA bot comment yet)"
  fi
  echo ""

  # ── 9. Overall Status Summary ──────────────────────────────────
  echo "============================================================"
  echo "  SUMMARY"
  echo "============================================================"

  # Count check statuses
  CHECKS_JSON=$(gh pr checks "$PR_NUMBER" --repo "$REPO" --json name,state 2>/dev/null || echo "[]")
  TOTAL=$(echo "$CHECKS_JSON" | jq 'length' 2>/dev/null || echo "0")
  PASS=$(echo "$CHECKS_JSON" | jq '[.[] | select(.state == "SUCCESS")] | length' 2>/dev/null || echo "0")
  FAIL=$(echo "$CHECKS_JSON" | jq '[.[] | select(.state == "FAILURE")] | length' 2>/dev/null || echo "0")
  PENDING=$(echo "$CHECKS_JSON" | jq '[.[] | select(.state == "PENDING" or .state == "QUEUED" or .state == "IN_PROGRESS")] | length' 2>/dev/null || echo "0")

  echo "  CI Checks: ${PASS}/${TOTAL} passed, ${FAIL} failed, ${PENDING} pending"
  echo "  CodeRabbit comments: ${CODERABBIT_COMMENTS}"
  echo ""

  if [ "$FAIL" -gt 0 ] 2>/dev/null; then
    echo "  ACTION REQUIRED: Fix CI failures"
    echo "  Failed checks:"
    echo "$CHECKS_JSON" | jq -r '.[] | select(.state == "FAILURE") | "    - \(.name)"' 2>/dev/null || true
  elif [ "$PENDING" -gt 0 ] 2>/dev/null; then
    echo "  WAITING: ${PENDING} checks still running"
  else
    echo "  ALL CHECKS PASSING"
  fi

  if [ "$CODERABBIT_COMMENTS" -gt 0 ] 2>/dev/null; then
    echo "  ACTION REQUIRED: Review and address CodeRabbit inline comments"
  fi
  echo ""
  echo "============================================================"

  # Return non-zero if there are failures or pending items
  if [ "$FAIL" -gt 0 ] 2>/dev/null; then
    return 1
  elif [ "$PENDING" -gt 0 ] 2>/dev/null; then
    return 2
  fi
  return 0
}

if [ "$WAIT" = true ]; then
  echo "Polling PR #${PR_NUMBER} (Ctrl+C to stop)..."
  while true; do
    poll_once
    rc=$?
    if [ $rc -eq 0 ]; then
      echo "All checks passed."
      break
    elif [ $rc -eq 1 ]; then
      echo "Failures detected. Stopping."
      break
    fi
    # rc=2 means pending — keep polling
    echo ""
    echo "Next poll in 60 seconds..."
    sleep 60
  done
else
  poll_once
fi
