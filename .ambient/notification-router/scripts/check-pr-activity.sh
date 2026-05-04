#!/bin/bash
# check-pr-activity.sh — Check a single PR for actionable activity.
#
# Usage: bash scripts/check-pr-activity.sh <PR_NUMBER> [--repo OWNER/REPO]
#
# Output: JSON object with actionable status and details.
# Exit 0 = actionable, Exit 1 = not actionable, Exit 2 = error.

set -euo pipefail

PR_NUMBER="${1:?Usage: check-pr-activity.sh <PR_NUMBER> [--repo OWNER/REPO]}"
shift
REPO="quay/quay"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
done

failing_checks=0
pending_checks=0
passing_checks=0
open_comments=0
changes_requested=false
approved=false

# --- CI Checks ---
checks_json=$(gh pr checks "$PR_NUMBER" --repo "$REPO" --json name,state,conclusion 2>/dev/null || echo "[]")
if [[ "$checks_json" != "[]" ]]; then
  failing_checks=$(echo "$checks_json" | jq '[.[] | select(.conclusion == "FAILURE" or .conclusion == "CANCELLED")] | length')
  pending_checks=$(echo "$checks_json" | jq '[.[] | select(.state != "COMPLETED")] | length')
  passing_checks=$(echo "$checks_json" | jq '[.[] | select(.conclusion == "SUCCESS")] | length')
fi

# --- Review Comments (top-level only = unresolved threads) ---
comments_json=$(gh api "repos/${REPO}/pulls/${PR_NUMBER}/comments" --jq '[.[] | select(.in_reply_to_id == null)]' 2>/dev/null || echo "[]")
open_comments=$(echo "$comments_json" | jq 'length')

# --- Review State ---
reviews_json=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json reviews --jq '.reviews' 2>/dev/null || echo "[]")
if [[ "$reviews_json" != "[]" ]]; then
  latest_states=$(echo "$reviews_json" | jq -r '[group_by(.author.login) | .[] | max_by(.submittedAt) | .state] | .[]')
  if echo "$latest_states" | grep -q "CHANGES_REQUESTED"; then
    changes_requested=true
  fi
  if echo "$latest_states" | grep -q "APPROVED"; then
    approved=true
  fi
fi

# --- Determine actionability ---
actionable=false
reasons=()

if [[ "$failing_checks" -gt 0 ]]; then
  actionable=true
  reasons+=("${failing_checks} failing CI checks")
fi

if [[ "$open_comments" -gt 0 ]]; then
  actionable=true
  reasons+=("${open_comments} review comments")
fi

if [[ "$changes_requested" == "true" ]]; then
  actionable=true
  reasons+=("changes requested by reviewer")
fi

if [[ "$approved" == "true" ]]; then
  actionable=true
  reasons+=("PR approved — may need merge or backport")
fi

# --- Output ---
if [[ ${#reasons[@]} -gt 0 ]]; then
  reasons_json=$(printf '%s\n' "${reasons[@]}" | jq -R . | jq -s .)
else
  reasons_json="[]"
fi

cat <<EOF
{
  "pr": ${PR_NUMBER},
  "actionable": ${actionable},
  "reasons": ${reasons_json},
  "ci": {
    "failing": ${failing_checks},
    "pending": ${pending_checks},
    "passing": ${passing_checks}
  },
  "reviews": {
    "open_comments": ${open_comments},
    "changes_requested": ${changes_requested},
    "approved": ${approved}
  }
}
EOF

if [[ "$actionable" == "true" ]]; then
  exit 0
else
  exit 1
fi
