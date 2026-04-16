#!/bin/bash
# check-ci.sh -- Quick CI status check for a PR.
#
# Usage: bash scripts/check-ci.sh <PR_NUMBER> [--repo owner/repo]

set -euo pipefail

PR_NUMBER="${1:?Usage: check-ci.sh <PR_NUMBER> [--repo owner/repo]}"
REPO="${3:-quay/quay}"

if [ "${2:-}" = "--repo" ] && [ -n "${3:-}" ]; then
  REPO="$3"
fi

echo "CI Status for PR #${PR_NUMBER} (${REPO})"
echo "──────────────────────────────────────────"

gh pr checks "$PR_NUMBER" --repo "$REPO" 2>/dev/null || true

echo ""
echo "── Summary ──"

CHECKS_JSON=$(gh pr checks "$PR_NUMBER" --repo "$REPO" --json name,state 2>/dev/null || echo "[]")
TOTAL=$(echo "$CHECKS_JSON" | jq 'length' 2>/dev/null || echo "0")
PASS=$(echo "$CHECKS_JSON" | jq '[.[] | select(.state == "SUCCESS")] | length' 2>/dev/null || echo "0")
FAIL=$(echo "$CHECKS_JSON" | jq '[.[] | select(.state == "FAILURE")] | length' 2>/dev/null || echo "0")
PENDING=$(echo "$CHECKS_JSON" | jq '[.[] | select(.state == "PENDING" or .state == "QUEUED" or .state == "IN_PROGRESS")] | length' 2>/dev/null || echo "0")

echo "Total: ${TOTAL}  Pass: ${PASS}  Fail: ${FAIL}  Pending: ${PENDING}"

if [ "$FAIL" -gt 0 ] 2>/dev/null; then
  echo ""
  echo "FAILED:"
  echo "$CHECKS_JSON" | jq -r '.[] | select(.state == "FAILURE") | "  - \(.name)"' 2>/dev/null
  exit 1
elif [ "$PENDING" -gt 0 ] 2>/dev/null; then
  echo ""
  echo "STILL RUNNING: ${PENDING} check(s) pending"
  exit 2
else
  echo ""
  echo "ALL CHECKS PASSING"
fi
