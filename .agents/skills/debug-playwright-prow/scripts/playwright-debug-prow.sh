#!/bin/bash
# playwright-debug-prow.sh -- Download and analyze Playwright CI artifacts from Prow/OpenShift CI.
#
# Usage:
#   bash .agents/skills/debug-playwright-prow/scripts/playwright-debug-prow.sh <PROW_URL>
#
# Prow URL formats accepted:
#   https://prow.ci.openshift.org/view/gs/<bucket>/<path>/<build_id>
#   https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/<bucket>/<path>/<build_id>/
#
# Exit codes:
#   0 — analyzed successfully
#   1 — error (no artifacts, bad input, download failure)
#   2 — run still in progress

set -euo pipefail

INPUT="${1:?Usage: playwright-debug-prow.sh <PROW_URL>}"

# --- Network limits ---
# Every fetch targets a public GCS object whose size is attacker-influenceable.
# Bound connect/transfer time and the maximum downloaded object size so an
# oversized artifact cannot exhaust local disk or hang the run.
CURL_TIMEOUT=(--connect-timeout 15 --max-time 300)
CURL_MAXSIZE=(--max-filesize 104857600) # 100 MiB per artifact
MAX_GCS_LIST_PAGES=20
MAX_DISCOVERED_ARTIFACTS=100

# --- URL Parsing ---
# Normalize the URL and extract GCS bucket, job path, and build ID.
#
# Prow view URL:
#   https://prow.ci.openshift.org/view/gs/BUCKET/logs/JOB_NAME/BUILD_ID
# GCSWeb URL:
#   https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/BUCKET/logs/JOB_NAME/BUILD_ID/

GCS_BUCKET=""
GCS_JOB_PATH=""
BUILD_ID=""
JOB_NAME=""

if [[ "$INPUT" =~ ^https://prow\.ci\.openshift\.org/view/gs/([^/]+)/(.+)/([0-9]+)/?$ ]]; then
  GCS_BUCKET="${BASH_REMATCH[1]}"
  GCS_JOB_PATH="${BASH_REMATCH[2]}"
  BUILD_ID="${BASH_REMATCH[3]}"
elif [[ "$INPUT" =~ ^https://gcsweb-ci[^/]*/gcs/([^/]+)/(.+)/([0-9]+)/?$ ]]; then
  GCS_BUCKET="${BASH_REMATCH[1]}"
  GCS_JOB_PATH="${BASH_REMATCH[2]}"
  BUILD_ID="${BASH_REMATCH[3]}"
else
  echo "ERROR: Unrecognized Prow URL format." >&2
  echo "Expected:" >&2
  echo "  https://prow.ci.openshift.org/view/gs/<bucket>/logs/<job_name>/<build_id>" >&2
  echo "  https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/<bucket>/logs/<job_name>/<build_id>/" >&2
  exit 1
fi

# Extract the job name (last path component before build ID)
JOB_NAME=$(basename "$GCS_JOB_PATH")

GCS_BASE="https://storage.googleapis.com/${GCS_BUCKET}/${GCS_JOB_PATH}/${BUILD_ID}"
GCSWEB_BASE="https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/${GCS_BUCKET}/${GCS_JOB_PATH}/${BUILD_ID}"
PROW_URL="https://prow.ci.openshift.org/view/gs/${GCS_BUCKET}/${GCS_JOB_PATH}/${BUILD_ID}"

# List objects below a known GCS prefix. The prefix is derived from the input
# Prow URL and discovered workflow layout; listed object names are data only.
# Keep pagination and each response bounded before selecting expected files.
GCS_LIST_KEYS=()
list_gcs_keys() {
  local full_prefix="$1"
  local prefix="${full_prefix#https://storage.googleapis.com/${GCS_BUCKET}/}"
  local marker=""
  local page=0
  local response=""
  local next_marker=""
  local key=""

  GCS_LIST_KEYS=()
  while [ "$page" -lt "$MAX_GCS_LIST_PAGES" ]; do
    page=$((page + 1))
    local curl_args=(
      -sfL
      "${CURL_TIMEOUT[@]}"
      "${CURL_MAXSIZE[@]}"
      --get
      --data-urlencode "prefix=${prefix}"
      --data-urlencode "max-keys=1000"
    )
    if [ -n "$marker" ]; then
      curl_args+=(--data-urlencode "marker=${marker}")
    fi

    response=$(curl "${curl_args[@]}" "https://storage.googleapis.com/${GCS_BUCKET}") || return 1
    while IFS= read -r key; do
      [ -n "$key" ] && GCS_LIST_KEYS+=("https://storage.googleapis.com/${GCS_BUCKET}/${key}")
    done < <(printf '%s' "$response" | grep -oP '(?<=<Key>)[^<]+' || true)

    next_marker=$(printf '%s' "$response" | grep -oP '(?<=<NextMarker>)[^<]+' || true)
    if [ -z "$next_marker" ]; then
      return 0
    fi
    if [ "$next_marker" = "$marker" ]; then
      echo "WARNING: GCS listing marker did not advance for ${prefix}" >&2
      return 1
    fi
    marker="$next_marker"
  done

  echo "WARNING: GCS listing reached ${MAX_GCS_LIST_PAGES} pages for ${prefix}" >&2
  return 1
}

json_array() {
  if [ "$#" -eq 0 ]; then
    printf '[]'
  else
    printf '%s\n' "$@" | jq -R . | jq -s .
  fi
}

echo "Job: $JOB_NAME" >&2
echo "Build ID: $BUILD_ID" >&2
echo "GCS base: $GCS_BASE" >&2

# --- Check Job Status ---
# Download prowjob.json to check if the job has completed.
PROWJOB_JSON=$(curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" "${GCS_BASE}/prowjob.json" 2>/dev/null) || {
  echo "ERROR: Could not fetch prowjob.json — job may not exist or GCS is unreachable" >&2
  exit 1
}

JOB_STATUS=$(echo "$PROWJOB_JSON" | jq -r '.status.state // "unknown"')

if [ "$JOB_STATUS" != "success" ] && [ "$JOB_STATUS" != "failure" ] && [ "$JOB_STATUS" != "aborted" ] && [ "$JOB_STATUS" != "error" ]; then
  echo "Job is still $JOB_STATUS (not completed yet)" >&2
  jq -n --arg build_id "$BUILD_ID" --arg prow_url "$PROW_URL" --arg status "$JOB_STATUS" \
    '{build_id: $build_id, prow_url: $prow_url, status: $status, error: "job not completed"}'
  exit 2
fi

echo "Job status: $JOB_STATUS" >&2

# --- Discover Artifacts ---
# The e2e step name for Quay Playwright tests is "quay-test-e2e".
# Artifacts live under: artifacts/<workflow>/<step>/artifacts/
# We probe for the Playwright JSON reporter output (results.json) to locate them.
STEP_NAME="quay-test-e2e"

WORK_DIR=$(mktemp -d)
echo "Downloading artifacts to $WORK_DIR ..." >&2

RESULTS_FOUND=false
ARTIFACT_BASE=""

# Probe for results.json at the expected artifact paths.
# Pattern: artifacts/{workflow}/{step}/artifacts/results.json
for step in "$STEP_NAME" "e2e" "e2e-test" "quay-e2e"; do
  PROBE_URL="${GCS_BASE}/artifacts/${step}/artifacts/results.json"
  if curl -sfL "${CURL_TIMEOUT[@]}" --head "$PROBE_URL" >/dev/null 2>&1; then
    ARTIFACT_BASE="${GCS_BASE}/artifacts/${step}/artifacts"
    STEP_NAME="$step"
    RESULTS_FOUND=true
    echo "  Found artifacts at: artifacts/${step}/artifacts/" >&2
    break
  fi

  # Also try a flat layout (artifacts/step/results.json)
  PROBE_URL="${GCS_BASE}/artifacts/${step}/results.json"
  if curl -sfL "${CURL_TIMEOUT[@]}" --head "$PROBE_URL" >/dev/null 2>&1; then
    ARTIFACT_BASE="${GCS_BASE}/artifacts/${step}"
    STEP_NAME="$step"
    RESULTS_FOUND=true
    echo "  Found artifacts at: artifacts/${step}/ (flat layout)" >&2
    break
  fi
done

# If not found with simple names, list the workflow directories via the GCS XML
# API and probe results.json under each.
if [ "$RESULTS_FOUND" != "true" ]; then
  echo "  Probing GCS for results.json location..." >&2
  GCS_LIST_URL="https://storage.googleapis.com/${GCS_BUCKET}?prefix=${GCS_JOB_PATH}/${BUILD_ID}/artifacts/&delimiter=/"
  ARTIFACT_DIRS=$(curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" "$GCS_LIST_URL" 2>/dev/null | grep -oP '(?<=<Prefix>)[^<]+' || true)

  for dir in $ARTIFACT_DIRS; do
    # dir looks like: logs/JOB_NAME/BUILD_ID/artifacts/WORKFLOW_NAME/
    PROBE_URL="https://storage.googleapis.com/${GCS_BUCKET}/${dir}${STEP_NAME}/artifacts/results.json"
    if curl -sfL "${CURL_TIMEOUT[@]}" --head "$PROBE_URL" >/dev/null 2>&1; then
      ARTIFACT_BASE="https://storage.googleapis.com/${GCS_BUCKET}/${dir}${STEP_NAME}/artifacts"
      RESULTS_FOUND=true
      echo "  Found artifacts at: ${dir}${STEP_NAME}/artifacts/" >&2
      break
    fi
  done
fi

# Some workflows nest the step one level deeper than the workflow dir (e.g.
# artifacts/e2e/quay-test-playwright/); list each workflow dir itself and
# probe results.json under each step prefix found there.
if [ "$RESULTS_FOUND" != "true" ]; then
  for dir in $ARTIFACT_DIRS; do
    STEP_LIST_URL="https://storage.googleapis.com/${GCS_BUCKET}?prefix=${dir}&delimiter=/"
    STEP_DIRS=$(curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" "$STEP_LIST_URL" 2>/dev/null | grep -oP '(?<=<Prefix>)[^<]+' || true)
    for stepdir in $STEP_DIRS; do
      PROBE_URL="https://storage.googleapis.com/${GCS_BUCKET}/${stepdir}artifacts/results.json"
      if curl -sfL "${CURL_TIMEOUT[@]}" --head "$PROBE_URL" >/dev/null 2>&1; then
        ARTIFACT_BASE="https://storage.googleapis.com/${GCS_BUCKET}/${stepdir}artifacts"
        STEP_NAME="${stepdir%/}"
        STEP_NAME="${STEP_NAME##*/}"
        RESULTS_FOUND=true
        echo "  Found artifacts at: ${stepdir}artifacts/" >&2
        break 2
      fi
    done
  done
fi

if [ "$RESULTS_FOUND" != "true" ]; then
  echo "ERROR: Could not locate results.json in artifacts" >&2
  echo "  This run may predate the Playwright JSON reporter (results.json)." >&2
  echo "  Browse the artifacts manually at: ${GCSWEB_BASE}/artifacts/" >&2
  exit 1
fi

# Normalize the E2E step and workflow bases so sibling artifacts resolve for
# both nested (.../<step>/artifacts) and flat (.../<step>) layouts.
case "$ARTIFACT_BASE" in
  */"$STEP_NAME"/artifacts)
    E2E_STEP_BASE="${ARTIFACT_BASE%/artifacts}"
    WORKFLOW_BASE="${ARTIFACT_BASE%/"$STEP_NAME"/artifacts}"
    ;;
  */"$STEP_NAME")
    E2E_STEP_BASE="$ARTIFACT_BASE"
    WORKFLOW_BASE="${ARTIFACT_BASE%/"$STEP_NAME"}"
    ;;
  *)
    echo "ERROR: unsupported E2E artifact path: ${ARTIFACT_BASE}" >&2
    exit 1
    ;;
esac

# --- Download Artifacts ---
HAS_BUILD_LOG=false
HAS_HTML_REPORT=false
HAS_CONTAINER_LOGS=false
HAS_JAEGER_TRACES=false
CONTAINER_LOG_FILES=()
REDACTED_CONTAINER_LOG_FILES=()
JAEGER_TRACE_FILES=()

# Download the Playwright JSON reporter output.
curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" "${ARTIFACT_BASE}/results.json" -o "$WORK_DIR/results.json" 2>/dev/null && {
  echo "  Downloaded: results.json" >&2
} || {
  echo "ERROR: failed to download results.json" >&2
  exit 1
}

if [ ! -s "$WORK_DIR/results.json" ]; then
  echo "ERROR: downloaded results.json is empty" >&2
  exit 1
fi

if ! jq -e . "$WORK_DIR/results.json" >/dev/null 2>&1; then
  echo "ERROR: downloaded results.json is not valid JSON" >&2
  exit 1
fi
if ! jq -e 'type == "object" and (has("stats") or has("suites") or has("results"))' \
    "$WORK_DIR/results.json" >/dev/null; then
  echo "ERROR: downloaded results.json is valid JSON but missing expected top-level keys" >&2
  echo "  Expected an object with at least one of: stats, suites, results" >&2
  exit 1
fi

# Download build log from the E2E step root.
BUILD_LOG_URL="${E2E_STEP_BASE}/build-log.txt"
curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" "$BUILD_LOG_URL" -o "$WORK_DIR/build-log.txt" 2>/dev/null && {
  HAS_BUILD_LOG=true
  echo "  Downloaded: build-log.txt" >&2
} || echo "  Not available: build-log.txt" >&2

# Check for HTML report
HTML_REPORT_URL="${ARTIFACT_BASE}/index.html"
if curl -sfL "${CURL_TIMEOUT[@]}" --head "$HTML_REPORT_URL" >/dev/null 2>&1; then
  HAS_HTML_REPORT=true
  echo "  Available: HTML report (index.html)" >&2
fi

# Check for pod-qualified Quay container logs in gather-extra artifacts.
# GCS has a flat namespace: list the known pods prefix rather than probing a
# few legacy object names. Keep a concatenated quay.log for compatibility.
GATHER_EXTRA_BASE="${WORKFLOW_BASE}/gather-extra/artifacts"
mkdir -p "$WORK_DIR/container-logs"
if list_gcs_keys "${GATHER_EXTRA_BASE}/pods/"; then
  downloaded_logs=0
  for key in "${GCS_LIST_KEYS[@]}"; do
    log_name="${key#"${GATHER_EXTRA_BASE}/pods/"}"
    if [[ "$log_name" =~ ^[A-Za-z0-9._-]+_quay-app\.log$ ]]; then
      echo "  Discovered Quay pod log: ${log_name}" >&2
      if [ "$downloaded_logs" -ge "$MAX_DISCOVERED_ARTIFACTS" ]; then
        echo "  WARNING: skipping additional Quay pod logs after ${MAX_DISCOVERED_ARTIFACTS}" >&2
        continue
      fi
      downloaded_logs=$((downloaded_logs + 1))
      log_path="$WORK_DIR/container-logs/${log_name}"
      if ! curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" \
        "${GATHER_EXTRA_BASE}/pods/${log_name}" -o "$log_path" 2>/dev/null; then
        echo "  Could not download Quay pod log: ${log_name}" >&2
        rm -f "$log_path"
      elif [ ! -s "$log_path" ]; then
        echo "  Ignoring empty Quay pod log: ${log_name}" >&2
        rm -f "$log_path"
      elif grep -Fqx 'This file contained potentially sensitive information and has been removed.' "$log_path"; then
        REDACTED_CONTAINER_LOG_FILES+=("$log_name")
        echo "  Redacted Quay pod log: ${log_name}" >&2
        rm -f "$log_path"
      else
        CONTAINER_LOG_FILES+=("$log_name")
        cat "$log_path" >>"$WORK_DIR/container-logs/quay.log"
        printf '\n' >>"$WORK_DIR/container-logs/quay.log"
        HAS_CONTAINER_LOGS=true
        echo "  Downloaded Quay pod log: ${log_name}" >&2
      fi
    fi
  done
else
  echo "  Could not list Quay pod logs under gather-extra" >&2
fi
if [ "$HAS_CONTAINER_LOGS" != "true" ]; then
  rmdir "$WORK_DIR/container-logs" 2>/dev/null || true
  echo "  Not available: usable Quay pod logs under gather-extra" >&2
fi

# Jaeger artifacts are uploaded by a separate sibling workflow step. The
# normalized workflow base works across release variants and artifact layouts.
JAEGER_STEP_NAME="quay-gather-jaeger-traces"
JAEGER_ARTIFACT_BASE="${WORKFLOW_BASE}/${JAEGER_STEP_NAME}/artifacts/jaeger-traces"
mkdir -p "$WORK_DIR/jaeger-traces"
if list_gcs_keys "${JAEGER_ARTIFACT_BASE}/"; then
  downloaded_jaeger_files=0
  for key in "${GCS_LIST_KEYS[@]}"; do
    jaeger_file="${key#"${JAEGER_ARTIFACT_BASE}/"}"
    if [[ "$jaeger_file" == "traces.json" || "$jaeger_file" == "trace-metrics.json" || "$jaeger_file" == "api-coverage.json" || "$jaeger_file" =~ ^traces-[A-Za-z0-9._-]+\.json$ ]]; then
      echo "  Discovered Jaeger artifact: ${jaeger_file}" >&2
      if [ "$downloaded_jaeger_files" -ge "$MAX_DISCOVERED_ARTIFACTS" ]; then
        echo "  WARNING: skipping additional Jaeger artifacts after ${MAX_DISCOVERED_ARTIFACTS}" >&2
        continue
      fi
      downloaded_jaeger_files=$((downloaded_jaeger_files + 1))
      trace_path="$WORK_DIR/jaeger-traces/${jaeger_file}"
      if curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" \
        "${JAEGER_ARTIFACT_BASE}/${jaeger_file}" -o "$trace_path" 2>/dev/null; then
        if jq -e . "$trace_path" >/dev/null; then
          HAS_JAEGER_TRACES=true
          if [[ "$jaeger_file" == "traces.json" || "$jaeger_file" =~ ^traces-[A-Za-z0-9._-]+\.json$ ]]; then
            JAEGER_TRACE_FILES+=("$jaeger_file")
          fi
          echo "  Downloaded Jaeger artifact: ${jaeger_file}" >&2
        else
          echo "  Ignoring invalid Jaeger artifact JSON: ${jaeger_file}" >&2
          rm -f "$trace_path"
        fi
      else
        echo "  Could not download Jaeger artifact: ${jaeger_file}" >&2
        rm -f "$trace_path"
      fi
    fi
  done
else
  echo "  Could not list Jaeger artifacts" >&2
fi
if [ "$HAS_JAEGER_TRACES" != "true" ]; then
  rmdir "$WORK_DIR/jaeger-traces" 2>/dev/null || true
  echo "  Not available: valid Jaeger trace artifacts" >&2
fi

CONTAINER_LOG_FILES_JSON=$(json_array "${CONTAINER_LOG_FILES[@]}")
REDACTED_CONTAINER_LOG_FILES_JSON=$(json_array "${REDACTED_CONTAINER_LOG_FILES[@]}")
JAEGER_TRACE_FILES_JSON=$(json_array "${JAEGER_TRACE_FILES[@]}")

# --- Build Report URLs ---
HTML_REPORT_GCSWEB=""
if [ "$HAS_HTML_REPORT" = "true" ]; then
  # Convert GCS URL to GCSWeb URL for browsable access
  ARTIFACT_PATH="${ARTIFACT_BASE#https://storage.googleapis.com/}"
  HTML_REPORT_GCSWEB="https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/${ARTIFACT_PATH}/index.html"
fi

# --- Derive Report from results.json ---
# Everything below is derived from Playwright's JSON reporter. Test status
# classifies each test: expected (passed), unexpected (failed), flaky, skipped.
# Attachment paths in results.json are absolute container paths under
# .../test-results/<dir>/<file>; the <dir>/<file> tail is uploaded next to
# results.json, so map it onto ARTIFACT_BASE for a browsable URL.
jq \
  --arg build_id "$BUILD_ID" \
  --arg job_name "$JOB_NAME" \
  --arg prow_url "$PROW_URL" \
  --arg gcsweb_url "$GCSWEB_BASE" \
  --arg job_status "$JOB_STATUS" \
  --arg artifacts_dir "$WORK_DIR" \
  --arg artifact_base_url "$ARTIFACT_BASE" \
  --arg html_report_url "$HTML_REPORT_GCSWEB" \
  --argjson has_build_log "$HAS_BUILD_LOG" \
  --argjson has_container_logs "$HAS_CONTAINER_LOGS" \
  --argjson has_jaeger_traces "$HAS_JAEGER_TRACES" \
  --argjson container_log_files "$CONTAINER_LOG_FILES_JSON" \
  --argjson redacted_container_log_files "$REDACTED_CONTAINER_LOG_FILES_JSON" \
  --argjson jaeger_trace_files "$JAEGER_TRACE_FILES_JSON" \
  --arg jaeger_artifact_base_url "$JAEGER_ARTIFACT_BASE" \
  '
  def strip_ansi: if type == "string" then gsub("[[:cntrl:]]\\[[0-9;]*m"; "") else . end;
  [.. | objects | select(has("specs")) | .specs[]] as $specs
  | ((.stats.expected + .stats.unexpected + .stats.flaky + .stats.skipped)) as $total
  | {
      build_id: $build_id,
      job_name: $job_name,
      prow_url: $prow_url,
      gcsweb_url: $gcsweb_url,
      job_status: $job_status,
      artifacts_dir: $artifacts_dir,
      artifact_base_url: $artifact_base_url,
      html_report_url: $html_report_url,
      has_build_log: $has_build_log,
      has_container_logs: $has_container_logs,
      has_jaeger_traces: $has_jaeger_traces,
      container_log_files: $container_log_files,
      redacted_container_log_files: $redacted_container_log_files,
      jaeger_trace_files: $jaeger_trace_files,
      jaeger_artifact_base_url: $jaeger_artifact_base_url,
      global_setup_failure: ($total == 0),
      stats: {
        total: $total,
        passed: .stats.expected,
        failed: .stats.unexpected,
        flaky: .stats.flaky,
        skipped: .stats.skipped,
        duration_s: (.stats.duration / 1000),
        start_time: .stats.startTime
      },
      failed: [ $specs[] as $s | $s.tests[] | select(.status == "unexpected") | {
        title: $s.title, file: $s.file, line: $s.line, project: .projectName,
        error_message: ((.results[-1].errors[0].message // .results[-1].error.message // "") | strip_ansi),
        attempts: [ .results[] | {
          retry: .retry, status: .status, duration: .duration,
          errors: [ .errors[].message | strip_ansi ],
          attachments: [ .attachments[] | { name, path, url: (if .path then ($artifact_base_url + "/" + (.path | sub(".*/test-results/"; ""))) else null end) } ]
        } ]
      } ],
      flaky: [ $specs[] as $s | $s.tests[] | select(.status == "flaky") | {
        title: $s.title, file: $s.file, line: $s.line,
        retries: ([.results[].retry] | max),
        first_error: ((.results[0].errors[0].message // .results[0].error.message // "") | strip_ansi)
      } ],
      skipped: [ $specs[] as $s | $s.tests[] | select(.status == "skipped") | {
        title: $s.title, file: $s.file, line: $s.line,
        reason: ([.annotations[] | select(.type == "skip") | .description] | first)
      } ],
      interrupted: [ $specs[] as $s | $s.tests[] | select(any(.results[]; .status == "interrupted")) | {
        title: $s.title, file: $s.file, line: $s.line, project: .projectName
      } ],
      setup_errors: [ .errors[].message | strip_ansi ]
    }' "$WORK_DIR/results.json"
