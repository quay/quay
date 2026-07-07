#!/bin/bash
# playwright-debug.sh -- Download and analyze Playwright CI artifacts.
#
# Usage:
#   bash scripts/playwright-debug.sh <PR_NUMBER>
#   bash scripts/playwright-debug.sh <GHA_RUN_URL>
#
# Environment variables:
#   DEFAULT_REPO — GitHub org/repo (default: quay/quay)
#
# Exit codes:
#   0 — analyzed successfully
#   1 — error (no artifacts, bad input)
#   2 — run still in progress

set -euo pipefail

: "${DEFAULT_REPO:=quay/quay}"

INPUT="${1:?Usage: playwright-debug.sh <PR_NUMBER_OR_RUN_URL>}"

# --- Input Resolution ---
if [[ "$INPUT" =~ ^https://github\.com/.+/actions/runs/([0-9]+) ]]; then
  RUN_ID="${BASH_REMATCH[1]}"
  echo "Using run ID from URL: $RUN_ID" >&2
elif [[ "$INPUT" =~ ^[0-9]+$ ]]; then
  PR_NUMBER="$INPUT"
  echo "Resolving PR #${PR_NUMBER} to latest Playwright run..." >&2

  HEAD_SHA=$(gh pr view "$PR_NUMBER" --repo "$DEFAULT_REPO" --json headRefOid --jq '.headRefOid' 2>/dev/null)
  if [ -z "$HEAD_SHA" ]; then
    echo "ERROR: Could not resolve PR #${PR_NUMBER}" >&2
    exit 1
  fi

  RUN_ID=$(gh run list \
    --repo "$DEFAULT_REPO" \
    --workflow "web-playwright-ci.yaml" \
    --commit "$HEAD_SHA" \
    --json databaseId,conclusion \
    --jq '.[0].databaseId' \
    2>/dev/null)

  if [ -z "$RUN_ID" ] || [ "$RUN_ID" = "null" ]; then
    echo "ERROR: No Playwright CI run found for PR #${PR_NUMBER} (HEAD: ${HEAD_SHA})" >&2
    exit 1
  fi
  echo "Found run ID: $RUN_ID" >&2
else
  echo "ERROR: Input must be a PR number or GitHub Actions run URL" >&2
  exit 1
fi

# --- Run metadata ---
RUN_JSON=$(gh run view "$RUN_ID" --repo "$DEFAULT_REPO" --json conclusion,url,headSha,event,createdAt,status 2>/dev/null) || {
  echo "ERROR: Could not fetch run $RUN_ID" >&2
  exit 1
}
RUN_URL=$(echo "$RUN_JSON" | jq -r '.url')
RUN_CONCLUSION=$(echo "$RUN_JSON" | jq -r '.conclusion')
RUN_STATUS=$(echo "$RUN_JSON" | jq -r '.status')
HEAD_SHA=$(echo "$RUN_JSON" | jq -r '.headSha')

# Check if run is still in progress
if [ "$RUN_STATUS" != "completed" ]; then
  echo "Run $RUN_ID is still $RUN_STATUS (not completed yet)" >&2
  jq -n --arg run_id "$RUN_ID" --arg run_url "$RUN_URL" --arg status "$RUN_STATUS" \
    '{run_id: $run_id, run_url: $run_url, status: $status, error: "run not completed"}'
  exit 2
fi

# Resolve PR number if we started from a URL
if [ -z "${PR_NUMBER:-}" ]; then
  PR_NUMBER=$(gh api "repos/${DEFAULT_REPO}/actions/runs/${RUN_ID}" --jq '.pull_requests[0].number // empty' 2>/dev/null || echo "")
fi

# --- Artifact Download ---
# Caller is responsible for cleanup — artifacts_dir is returned in JSON output
WORK_DIR=$(mktemp -d)
echo "Downloading artifacts to $WORK_DIR ..." >&2

ARTIFACTS_JSON=$(gh api "repos/${DEFAULT_REPO}/actions/runs/${RUN_ID}/artifacts" --jq '[.artifacts[] | {name, size_in_bytes, expired}]' 2>/dev/null)

HAS_TEST_RESULTS=false
HAS_CONTAINER_LOGS=false
HAS_JAEGER_TRACES=false

for artifact_name in playwright-test-results quay-container-logs jaeger-traces; do
  ARTIFACT_INFO=$(echo "$ARTIFACTS_JSON" | jq -r --arg name "$artifact_name" '.[] | select(.name == $name)')
  if [ -z "$ARTIFACT_INFO" ]; then
    echo "  Not available: $artifact_name" >&2
    continue
  fi

  IS_EXPIRED=$(echo "$ARTIFACT_INFO" | jq -r '.expired')
  if [ "$IS_EXPIRED" = "true" ]; then
    echo "  Expired: $artifact_name" >&2
    continue
  fi

  gh run download "$RUN_ID" --repo "$DEFAULT_REPO" --name "$artifact_name" --dir "$WORK_DIR/$artifact_name" 2>/dev/null && {
    case "$artifact_name" in
      playwright-test-results) HAS_TEST_RESULTS=true ;;
      quay-container-logs) HAS_CONTAINER_LOGS=true ;;
      jaeger-traces) HAS_JAEGER_TRACES=true ;;
    esac
    echo "  Downloaded: $artifact_name" >&2
  } || echo "  Warning: failed to download $artifact_name" >&2
done

# --- Failure Categorization ---
if [ "$HAS_TEST_RESULTS" != "true" ] || [ ! -f "$WORK_DIR/playwright-test-results/results.json" ]; then
  echo "ERROR: No results.json found in artifacts" >&2
  exit 1
fi

RESULTS_FILE="$WORK_DIR/playwright-test-results/results.json"

# Check for global setup failure (no suites at all)
SUITE_COUNT=$(jq '.suites | length' "$RESULTS_FILE")
if [ "$SUITE_COUNT" -eq 0 ]; then
  STATS=$(jq '.stats' "$RESULTS_FILE")
  ERRORS=$(jq '[.errors[]? | (.message // "" | tostring)[0:500]]' "$RESULTS_FILE")
  jq -n \
    --arg run_id "$RUN_ID" \
    --arg run_url "$RUN_URL" \
    --arg run_conclusion "$RUN_CONCLUSION" \
    --arg head_sha "$HEAD_SHA" \
    --arg pr_number "${PR_NUMBER:-}" \
    --arg artifacts_dir "$WORK_DIR" \
    --argjson stats "$STATS" \
    --argjson errors "$ERRORS" \
    '{
      run_id: $run_id, run_url: $run_url, run_conclusion: $run_conclusion,
      head_sha: $head_sha, pr_number: $pr_number, artifacts_dir: $artifacts_dir,
      global_setup_failure: true, stats: $stats, errors: $errors
    }'
  exit 0
fi

STATS=$(jq '.stats' "$RESULTS_FILE")

# Use targeted recursion to avoid duplicates from `..`
FAILED=$(jq '
  def all_specs: .specs[]?, (.suites[]? | all_specs);
  [.suites[] | all_specs | select(.tests | any(.status == "unexpected")) |
  {
    title: .title,
    file: .file,
    line: .line,
    ok: .ok,
    tags: .tags,
    tests: [.tests[] | select(.status == "unexpected") | {
      status: .status,
      attempts: (.results | length),
      error_message: ((.results[-1].error.message // "no error message") | .[0:500]),
      error_stack: ((.results[-1].error.stack // null) | .[0:2000]),
      last_step: (.results[-1].steps[-1]?.title // null),
      attachments: [.results[-1].attachments[]? | select(.name == "screenshot" or .name == "video" or (.name | test("trace"))) | {name, path}],
      results: [.results[] | {status, retry, startTime, duration}]
    }]
  }]' "$RESULTS_FILE")

FLAKY=$(jq '
  def all_specs: .specs[]?, (.suites[]? | all_specs);
  [.suites[] | all_specs | select(.tests | any(.status == "flaky")) |
  {
    title: .title,
    file: .file,
    line: .line,
    tags: .tags,
    tests: [.tests[] | select(.status == "flaky") | {
      results: [.results[] | {status, retry, startTime, duration}]
    }]
  }]' "$RESULTS_FILE")

# Detect interrupted tests (worker crashes)
INTERRUPTED=$(jq '
  def all_specs: .specs[]?, (.suites[]? | all_specs);
  [.suites[] | all_specs |
  select(.tests | any(.results | any(.status == "interrupted"))) |
  {title: .title, file: .file, line: .line}]' "$RESULTS_FILE")

# Derive surge report URL
SURGE_URL=""
if [ -n "${PR_NUMBER:-}" ]; then
  SURGE_URL="https://quay-playwright-pr-${PR_NUMBER}.surge.sh"
fi

# --- Output ---
jq -n \
  --arg run_id "$RUN_ID" \
  --arg run_url "$RUN_URL" \
  --arg run_conclusion "$RUN_CONCLUSION" \
  --arg head_sha "$HEAD_SHA" \
  --arg pr_number "${PR_NUMBER:-}" \
  --arg surge_url "$SURGE_URL" \
  --arg artifacts_dir "$WORK_DIR" \
  --argjson has_container_logs "$HAS_CONTAINER_LOGS" \
  --argjson has_jaeger_traces "$HAS_JAEGER_TRACES" \
  --argjson stats "$STATS" \
  --argjson failed "$FAILED" \
  --argjson flaky "$FLAKY" \
  --argjson interrupted "$INTERRUPTED" \
  '{
    run_id: $run_id,
    run_url: $run_url,
    run_conclusion: $run_conclusion,
    head_sha: $head_sha,
    pr_number: $pr_number,
    surge_url: $surge_url,
    artifacts_dir: $artifacts_dir,
    has_container_logs: $has_container_logs,
    has_jaeger_traces: $has_jaeger_traces,
    stats: $stats,
    failed: $failed,
    flaky: $flaky,
    interrupted: $interrupted
  }'
