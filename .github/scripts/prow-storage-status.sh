#!/usr/bin/env bash
# Usage: prow-storage-status.sh <pr-number> <sha> [--wait]
# Reports the storage Prow jobs at a master PR head as one commit status.
# With --wait, polls until they finish or the deadline passes.
set -euo pipefail

pr=$1
sha=$2
wait=${3:-}
repo=$GITHUB_REPOSITORY
status_context="CI / Prow / E2E"
storage_contexts=(ci/prow/aws-s3 ci/prow/gcp-gcs ci/prow/azure-blob)
interval=${PROW_STATUS_POLL_SECONDS:-300}
# Past the 4h Prow pod timeout, under the 6h hosted-runner cap.
deadline=$(($(date +%s) + ${PROW_STATUS_DEADLINE_SECONDS:-18000}))
target_url="$GITHUB_SERVER_URL/$repo/actions/runs/$GITHUB_RUN_ID"

# An API error exits non-zero, so the waiter fails instead of passing as a stale head.
current() {
  local pr_json
  pr_json=$(gh api "repos/$repo/pulls/$pr") || exit 1
  jq -e --arg sha "$sha" '.state == "open" and .base.ref == "master" and .head.sha == $sha' <<<"$pr_json" >/dev/null
}

post() {
  current || exit 0
  gh api -X POST "repos/$repo/statuses/$sha" -f state="$1" -f context="$status_context" \
    -f description="$2" -f target_url="$target_url" >/dev/null
}

# Sets state (success|failure|pending) and description from the latest storage statuses.
aggregate() {
  local statuses s c waiting=()
  statuses=$(gh api --paginate "repos/$repo/commits/$sha/status?per_page=100" \
    --jq '.statuses[] | "\(.context) \(.state)"')
  for c in "${storage_contexts[@]}"; do
    s=$(awk -v c="$c" '$1 == c { print $2; exit }' <<<"$statuses")
    case $s in
    failure | error)
      state=failure description="$c failed"
      return
      ;;
    success) ;;
    *) waiting+=("$c") ;;
    esac
  done
  if [ ${#waiting[@]} -eq 0 ]; then
    state=success description="storage jobs passed"
  else
    state=pending description="waiting for ${waiting[*]}"
  fi
}

# The pipeline controller creates the storage contexts only when the PR changes one of these files.
files=$(gh api --paginate "repos/$repo/pulls/$pr/files" --jq '.[].filename')
if ! grep -qxE 'requirements\.txt|requirements-build\.txt|constraints\.txt|pyproject\.toml' <<<"$files"; then
  post success "no storage jobs selected"
  exit 0
fi

if [ "$wait" != --wait ]; then
  aggregate
  post "$state" "$description"
  exit 0
fi

post pending "waiting for storage jobs"
while :; do
  # A push or retarget makes this head stale; stop rather than poll it to the deadline.
  current || exit 0
  aggregate
  if [ "$state" != pending ]; then
    post "$state" "$description"
    exit 0
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    post failure "timed out ${description}"
    exit 0
  fi
  sleep "$interval"
done
