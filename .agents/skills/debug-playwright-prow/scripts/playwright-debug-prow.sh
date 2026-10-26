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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=collector-lib.sh
. "$SCRIPT_DIR/collector-lib.sh"

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

echo "Job: $JOB_NAME" >&2
echo "Build ID: $BUILD_ID" >&2
echo "GCS base: $GCS_BASE" >&2

# --- Scratch Storage ---
# Never use system /tmp: downloaded CI artifacts stay under the repo's
# gitignored tmp/ so a successful run's artifacts_dir is easy to find inside
# the workspace instead of orphaned somewhere outside it. (A failed run's
# scratch dir is removed by the EXIT trap below, not left behind.)
if REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null); then
  :
else
  REPO_ROOT="$SCRIPT_DIR"
  echo "WARNING: not inside a git work tree; using the script directory ($REPO_ROOT) as the repo root for scratch storage" >&2
fi
mkdir -p "$REPO_ROOT/tmp"
WORK_DIR=$(mktemp -d "$REPO_ROOT/tmp/playwright-prow.XXXXXX")
echo "Downloading artifacts to $WORK_DIR ..." >&2

# A non-zero exit means the run did not produce a usable artifacts_dir
# (error, or job still in progress with nothing downloaded yet); remove the
# scratch dir instead of orphaning it. A zero exit leaves it in place since
# its path is advertised to the caller as artifacts_dir.
cleanup_work_dir_on_failure() {
  local rc=$?
  if [ "$rc" -ne 0 ]; then
    rm -rf "$WORK_DIR"
  fi
}
trap cleanup_work_dir_on_failure EXIT

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

# --- Routing Records: prowjob.json ---
# Already fetched above to check job status; persist it alongside the other
# routing records so a triager never has to re-fetch it from GCS.
PROWJOB_URL="${GCS_BASE}/prowjob.json"
PROWJOB_PATH="$WORK_DIR/prowjob.json"
printf '%s' "$PROWJOB_JSON" >"$PROWJOB_PATH"
PROWJOB_STATUS="downloaded"

# --- Routing Records: clone-records.json / finished.json ---
# clone-records.json is ci-operator's log of the sparse source clone(s) it
# performed; finished.json is the build-root Prow job's overall result, not
# the e2e step's result. Both feed the provenance fields derived below.
CLONE_RECORDS_URL="${GCS_BASE}/clone-records.json"
CLONE_RECORDS_PATH="$WORK_DIR/clone-records.json"
if curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" "$CLONE_RECORDS_URL" -o "$CLONE_RECORDS_PATH" 2>/dev/null && [ -s "$CLONE_RECORDS_PATH" ] && jq -e . "$CLONE_RECORDS_PATH" >/dev/null 2>&1; then
  CLONE_RECORDS_STATUS="downloaded"
  echo "  Downloaded: clone-records.json" >&2
else
  rm -f "$CLONE_RECORDS_PATH"
  CLONE_RECORDS_PATH=""
  CLONE_RECORDS_STATUS="unavailable"
  echo "  Not available: clone-records.json" >&2
fi

FINISHED_URL="${GCS_BASE}/finished.json"
FINISHED_PATH="$WORK_DIR/finished.json"
if curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" "$FINISHED_URL" -o "$FINISHED_PATH" 2>/dev/null && [ -s "$FINISHED_PATH" ] && jq -e . "$FINISHED_PATH" >/dev/null 2>&1; then
  FINISHED_STATUS="downloaded"
  echo "  Downloaded: finished.json" >&2
else
  rm -f "$FINISHED_PATH"
  FINISHED_PATH=""
  FINISHED_STATUS="unavailable"
  echo "  Not available: finished.json" >&2
fi

parse_clone_records "$CLONE_RECORDS_PATH"
parse_finished "$FINISHED_PATH"

# finished.json .revision is a fallback for the base ref, used whenever
# clone-records.json could not supply one for any reason.
if [ -z "$SOURCE_CLONE_REF" ] && [ -n "$FINISHED_REVISION" ]; then
  SOURCE_CLONE_REF_REASON="$SOURCE_CLONE_REF_REASON; using finished.json .revision, which may be a commit SHA rather than a ref"
  SOURCE_CLONE_REF="$FINISHED_REVISION"
elif [ -z "$SOURCE_CLONE_REF" ] && [ -z "$SOURCE_CLONE_REF_REASON" ]; then
  SOURCE_CLONE_REF_REASON="clone-records.json has no refs.base_ref and finished.json has no .revision"
fi

# --- Routing Records: top-level run build log ---
# This is the top-level ci-operator log for the whole run, distinct from the
# step-local build-log.txt fetched below from the e2e step's own artifact
# directory.
TOP_LEVEL_BUILD_LOG_URL="${GCS_BASE}/build-log.txt"
TOP_LEVEL_BUILD_LOG_PATH="$WORK_DIR/top-level-build-log.txt"
if curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" "$TOP_LEVEL_BUILD_LOG_URL" -o "$TOP_LEVEL_BUILD_LOG_PATH" 2>/dev/null && [ -s "$TOP_LEVEL_BUILD_LOG_PATH" ]; then
  TOP_LEVEL_BUILD_LOG_STATUS="downloaded"
  echo "  Downloaded: top-level-build-log.txt" >&2
else
  rm -f "$TOP_LEVEL_BUILD_LOG_PATH"
  TOP_LEVEL_BUILD_LOG_PATH=""
  TOP_LEVEL_BUILD_LOG_STATUS="unavailable"
  echo "  Not available: top-level build log" >&2
fi

# --- Discover Artifacts ---
# The e2e step name for Quay Playwright tests is "quay-test-e2e".
# Artifacts live under: artifacts/<workflow>/<step>/artifacts/
# We probe for the Playwright JSON reporter output (results.json) to locate them.
STEP_NAME="quay-test-e2e"

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
    # STEP_NAME still holds its initial default here (this block only runs
    # when the first-pass loop above found nothing); the nested fallback
    # below probes the other step-name candidates against listed step dirs.
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
      # Restrict probing to directories whose leaf name matches a known
      # Playwright step, so a multi-step workflow whose unrelated sibling
      # also uploads results.json can never be selected. quay-test-playwright
      # is included alongside the four e2e names as another step that runs
      # Playwright.
      candidate_step="${stepdir%/}"
      candidate_step="${candidate_step##*/}"
      case "$candidate_step" in
        quay-test-e2e | e2e | e2e-test | quay-e2e | quay-test-playwright) ;;
        *) continue ;;
      esac
      PROBE_URL="https://storage.googleapis.com/${GCS_BUCKET}/${stepdir}artifacts/results.json"
      if curl -sfL "${CURL_TIMEOUT[@]}" --head "$PROBE_URL" >/dev/null 2>&1; then
        ARTIFACT_BASE="https://storage.googleapis.com/${GCS_BUCKET}/${stepdir}artifacts"
        STEP_NAME="$candidate_step"
        RESULTS_FOUND=true
        echo "  Found artifacts at: ${stepdir}artifacts/" >&2
        break 2
      fi
    done
  done
fi

if [ "$RESULTS_FOUND" != "true" ]; then
  echo "ERROR: Could not locate results.json in artifacts" >&2
  echo "  Tried step names: quay-test-e2e, e2e, e2e-test, quay-e2e, quay-test-playwright" >&2
  echo "  If this job uses a different step name, results.json was not found under any candidate." >&2
  echo "  This run may also predate the Playwright JSON reporter (results.json)." >&2
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

# A shape that merely parses (e.g. {} or []) is not enough: require the
# specific fields the jq emit below actually reads, so a schema-empty file
# does not pass through into misleading diagnostic output.
if ! jq -e '
    type == "object"
    and (.stats | type) == "object"
    and ([.stats.expected, .stats.unexpected, .stats.flaky, .stats.skipped] | all(type == "number"))
    and (.suites | type) == "array"
    and (.config | type) == "object"
  ' "$WORK_DIR/results.json" >/dev/null 2>&1; then
  echo "ERROR: downloaded results.json is valid JSON but missing the Playwright reporter shape" >&2
  echo "  Expected an object with numeric stats.expected/unexpected/flaky/skipped, an array suites, and an object config" >&2
  exit 1
fi

# --- Routing Records: JUnit ---
# JUnit output lives next to results.json under ARTIFACT_BASE. There is
# normally one file (junit_playwright.xml), but list the prefix rather than
# probing a fixed name so a sharded run's multiple JUnit files are all
# representable.
JUNIT_RECORDS=()
mkdir -p "$WORK_DIR/junit"
if list_gcs_keys "${ARTIFACT_BASE}/"; then
  downloaded_junit=0
  for key in "${GCS_LIST_KEYS[@]}"; do
    junit_name="${key#"${ARTIFACT_BASE}/"}"
    if [[ "$junit_name" =~ ^[A-Za-z0-9._-]*junit[A-Za-z0-9._-]*\.xml$ ]]; then
      echo "  Discovered JUnit file: ${junit_name}" >&2
      if [ "$downloaded_junit" -ge "$MAX_DISCOVERED_ARTIFACTS" ]; then
        echo "  WARNING: skipping additional JUnit files after ${MAX_DISCOVERED_ARTIFACTS}" >&2
        continue
      fi
      downloaded_junit=$((downloaded_junit + 1))
      junit_path="$WORK_DIR/junit/${junit_name}"
      if curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" "$key" -o "$junit_path" 2>/dev/null && [ -s "$junit_path" ]; then
        JUNIT_RECORDS+=("$(jq -nc --arg url "$key" --arg path "$junit_path" --arg status "downloaded" '{source_url: $url, local_path: $path, status: $status}')")
        echo "  Downloaded JUnit file: ${junit_name}" >&2
      else
        rm -f "$junit_path"
        JUNIT_RECORDS+=("$(jq -nc --arg url "$key" --arg status "unavailable" '{source_url: $url, local_path: null, status: $status}')")
        echo "  Could not download JUnit file: ${junit_name}" >&2
      fi
    fi
  done
else
  echo "  Could not list JUnit files under ${ARTIFACT_BASE}" >&2
fi
if [ "${#JUNIT_RECORDS[@]}" -eq 0 ]; then
  rmdir "$WORK_DIR/junit" 2>/dev/null || true
fi
JUNIT_RECORDS_JSON=$(json_object_array "${JUNIT_RECORDS[@]}")

# --- Attachment Validation ---
# Every attachment Playwright advertises (screenshot, video, trace), on
# results of any status, is downloaded once and classified before its URL is
# trusted:
# usable, redacted (the CI sensitive-content placeholder, same text already
# used to detect redacted pod logs above), or missing (download failed, or a
# trace zip that fails validation). A trace zip is only ever advertised as
# usable after both its magic bytes and `unzip -t` pass.
ATTACHMENT_STATUS_RECORDS=()
mkdir -p "$WORK_DIR/attachments"
HAVE_UNZIP=true
command -v unzip >/dev/null 2>&1 || HAVE_UNZIP=false

# Single source for the attachment URL-building expression: spliced into both
# this candidate query and build_attachments in the report filter below, so
# the two can never drift and silently break the attachment_status_map lookup.
ATTACHMENT_URL_JQ='$artifact_base_url + "/" + (.path | sub(".*/test-results/"; "") | split("/") | map(select(. != "..")) | join("/"))'

CANDIDATE_ATTACHMENTS_JSON=$(jq -c --arg artifact_base_url "$ARTIFACT_BASE" '
  [.. | objects | select(has("attachments")) | .attachments[]?
   | select(.path != null)
   | { name, url: ('"$ATTACHMENT_URL_JQ"') }
  ] | unique_by(.url)
' "$WORK_DIR/results.json")

attachment_count=0
while IFS= read -r candidate; do
  [ -z "$candidate" ] && continue
  attachment_count=$((attachment_count + 1))
  att_name=$(printf '%s' "$candidate" | jq -r '.name')
  att_url=$(printf '%s' "$candidate" | jq -r '.url')

  if [ "$attachment_count" -gt "$MAX_DISCOVERED_ARTIFACTS" ]; then
    echo "  WARNING: skipping additional attachment checks after ${MAX_DISCOVERED_ARTIFACTS}" >&2
    ATTACHMENT_STATUS_RECORDS+=("$(jq -nc --arg url "$att_url" '{url: $url, status: "missing", reason: "attachment check cap exceeded"}')")
    continue
  fi

  att_file="$WORK_DIR/attachments/attachment-${attachment_count}"
  status="missing"
  reason="download failed"
  if curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" "$att_url" -o "$att_file" 2>/dev/null && [ -s "$att_file" ]; then
    if grep -Fqx 'This file contained potentially sensitive information and has been removed.' "$att_file"; then
      status="redacted"
      reason="CI sensitive-content placeholder"
    elif [ "$att_name" = "trace" ]; then
      if [ "$(head -c 2 "$att_file")" != "PK" ]; then
        status="missing"
        reason="not a valid zip (bad magic bytes)"
      elif [ "$HAVE_UNZIP" = "true" ]; then
        if unzip -tq "$att_file" >/dev/null 2>&1; then
          status="usable"
          reason=""
        else
          status="missing"
          reason="unzip -t failed (corrupt archive)"
        fi
      else
        status="missing"
        reason="zip integrity check not performed (unzip unavailable)"
      fi
    else
      status="usable"
      reason=""
    fi
  fi
  rm -f "$att_file"
  ATTACHMENT_STATUS_RECORDS+=("$(jq -nc --arg url "$att_url" --arg status "$status" --arg reason "$reason" '{url: $url, status: $status, reason: ($reason | if . == "" then null else . end)}')")
done < <(printf '%s' "$CANDIDATE_ATTACHMENTS_JSON" | jq -c '.[]')
rmdir "$WORK_DIR/attachments" 2>/dev/null || true

ATTACHMENT_STATUS_MAP_JSON=$(json_object_array "${ATTACHMENT_STATUS_RECORDS[@]}" | jq -c 'map({(.url): {status, reason}}) | add // {}')

# Download build log from the E2E step root. This is the step-local log
# (distinct from the top-level run build log fetched above); has_build_log
# reports whether it was found.
BUILD_LOG_URL="${E2E_STEP_BASE}/build-log.txt"
STEP_BUILD_LOG_PATH="$WORK_DIR/build-log.txt"
if curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" "$BUILD_LOG_URL" -o "$STEP_BUILD_LOG_PATH" 2>/dev/null && [ -s "$STEP_BUILD_LOG_PATH" ]; then
  HAS_BUILD_LOG=true
  STEP_BUILD_LOG_STATUS="downloaded"
  echo "  Downloaded: build-log.txt" >&2
else
  rm -f "$STEP_BUILD_LOG_PATH"
  STEP_BUILD_LOG_PATH=""
  STEP_BUILD_LOG_STATUS="unavailable"
  echo "  Not available: build-log.txt" >&2
fi

parse_playwright_sha "$STEP_BUILD_LOG_PATH"

# Check for HTML report
HTML_REPORT_URL="${ARTIFACT_BASE}/index.html"
if curl -sfL "${CURL_TIMEOUT[@]}" --head "$HTML_REPORT_URL" >/dev/null 2>&1; then
  HAS_HTML_REPORT=true
  echo "  Available: HTML report (index.html)" >&2
fi

# index.html can itself be the CI redaction placeholder rather than a real
# report; a HEAD request alone cannot tell the two apart.
if [ "$HAS_HTML_REPORT" = "true" ]; then
  HTML_REPORT_HEAD=$(curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" -r 0-255 "$HTML_REPORT_URL" 2>/dev/null || true)
  if [ "$(classify_bytes "$HTML_REPORT_HEAD")" = "redacted" ]; then
    HAS_HTML_REPORT=false
    echo "  HTML report index.html is the CI redaction placeholder" >&2
  fi
fi

# --- Run-level Evidence Gaps ---
# Redacted or missing run-level artifacts that would otherwise look like
# silently absent evidence, distinct from the per-attachment statuses above
# (which cover individual test attachments, not run-level sources): the
# must-gather tarball, and the HTML report's data blobs.

EVIDENCE_GAPS=()

MUST_GATHER_URL="${WORKFLOW_BASE}/gather-must-gather/artifacts/must-gather.tar"
must_gather_status=$(classify_object_head "$MUST_GATHER_URL")
must_gather_record=$(must_gather_gap_record "$must_gather_status" "$MUST_GATHER_URL")
if [ -n "$must_gather_record" ]; then
  EVIDENCE_GAPS+=("$must_gather_record")
fi
if [ "$must_gather_status" = "not_found" ]; then
  echo "  gather-must-gather step did not run for this job (no must-gather.tar)" >&2
fi

if list_gcs_keys "${ARTIFACT_BASE}/data/"; then
  data_blob_count=0
  for key in "${GCS_LIST_KEYS[@]}"; do
    if [ "$data_blob_count" -ge "$MAX_DISCOVERED_ARTIFACTS" ]; then
      echo "  WARNING: skipping additional HTML-report data checks after ${MAX_DISCOVERED_ARTIFACTS}" >&2
      continue
    fi
    data_blob_count=$((data_blob_count + 1))
    blob_name="data/${key#"${ARTIFACT_BASE}/data/"}"
    blob_status=$(classify_object_head "$key")
    if [ "$blob_status" = "redacted" ]; then
      EVIDENCE_GAPS+=("$(jq -nc --arg name "$blob_name" --arg url "$key" '{artifact: $name, source_url: $url, status: "redacted", reason: "CI sensitive-content placeholder"}')")
    elif [ "$blob_status" = "missing" ]; then
      EVIDENCE_GAPS+=("$(jq -nc --arg name "$blob_name" --arg url "$key" '{artifact: $name, source_url: $url, status: "missing", reason: "range read failed"}')")
    elif [ "$blob_status" = "not_found" ] || [ "$blob_status" = "head_failed" ]; then
      EVIDENCE_GAPS+=("$(jq -nc --arg name "$blob_name" --arg url "$key" '{artifact: $name, source_url: $url, status: "missing", reason: "HEAD probe failed"}')")
    fi
  done
else
  echo "  Could not list HTML-report data blobs under ${ARTIFACT_BASE}/data/" >&2
fi

EVIDENCE_GAPS_JSON=$(json_object_array "${EVIDENCE_GAPS[@]}")

# --- Builder Diagnostics ---
# Lists a GCS prefix and downloads at most MAX_DISCOVERED_ARTIFACTS files
# from it into dest_dir, returning a JSON array of
# {name, source_url, local_path, status, first_lines}. An absent prefix
# (nothing found) returns [].
collect_builder_diagnostics() {
  local prefix="$1" dest_dir="$2"
  local records=()
  if ! list_gcs_keys "$prefix" || [ "${#GCS_LIST_KEYS[@]}" -eq 0 ]; then
    printf '[]'
    return
  fi
  mkdir -p "$dest_dir"
  local count=0
  local key name file_path lines
  for key in "${GCS_LIST_KEYS[@]}"; do
    if [ "$count" -ge "$MAX_DISCOVERED_ARTIFACTS" ]; then
      echo "  WARNING: skipping additional builder-diagnostics files after ${MAX_DISCOVERED_ARTIFACTS}" >&2
      continue
    fi
    count=$((count + 1))
    name="${key#"$prefix"}"
    if ! is_safe_flat_name "$name"; then
      echo "  WARNING: skipping builder-diagnostics key with unexpected name: ${name}" >&2
      records+=("$(jq -nc --arg name "$name" --arg url "$key" '{name: $name, source_url: $url, local_path: null, status: "unavailable", first_lines: []}')")
      continue
    fi
    file_path="$dest_dir/$name"
    if curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" "$key" -o "$file_path" 2>/dev/null && [ -s "$file_path" ]; then
      lines=$(first_lines_json "$file_path")
      records+=("$(jq -nc --arg name "$name" --arg url "$key" --arg path "$file_path" --argjson lines "$lines" '{name: $name, source_url: $url, local_path: $path, status: "downloaded", first_lines: $lines}')")
    else
      rm -f "$file_path"
      records+=("$(jq -nc --arg name "$name" --arg url "$key" '{name: $name, source_url: $url, local_path: null, status: "unavailable", first_lines: []}')")
    fi
  done
  if [ "${#records[@]}" -eq 0 ]; then
    printf '[]'
  else
    printf '%s\n' "${records[@]}" | jq -s .
  fi
}

BUILDER_DIAGNOSTICS_JSON=$(collect_builder_diagnostics "${ARTIFACT_BASE}/builder-diagnostics/" "$WORK_DIR/builder-diagnostics")

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

# --- Provenance ---
# Each field below is derived from an artifact already on disk. A field that
# cannot be derived that way is left empty (emitted as null downstream) with
# a reason explaining why, rather than guessed or reconstructed.
SOURCE_IMAGE_DIGEST=""
SOURCE_IMAGE_DIGEST_REASON=""
if [ -n "$TOP_LEVEL_BUILD_LOG_PATH" ] && [ -s "$TOP_LEVEL_BUILD_LOG_PATH" ]; then
  SOURCE_IMAGE_DIGEST=$(sed -E 's/\x1b\[[0-9;]*m//g' "$TOP_LEVEL_BUILD_LOG_PATH" | grep -oP 'Image \S*playwright\S* created\s+digest=\K\S+' | tail -1 || true)
  if [ -z "$SOURCE_IMAGE_DIGEST" ]; then
    SOURCE_IMAGE_DIGEST_REASON="no playwright runner image digest line found in the top-level build log"
  fi
else
  SOURCE_IMAGE_DIGEST_REASON="top-level build log was not downloaded"
fi

RELEASE_CONFIG_REVISION=$(printf '%s' "$PROWJOB_JSON" | jq -r '(.spec.extra_refs[]? | select(.org == "openshift" and .repo == "release") | .base_sha) // empty')
RELEASE_CONFIG_REVISION_REASON=""
if [ -z "$RELEASE_CONFIG_REVISION" ]; then
  RELEASE_CONFIG_REVISION_REASON="prowjob.json has no openshift/release extra_refs entry with a base_sha for this job"
fi

# The collector never sends credentials; every GCS request above used the
# public, unauthenticated API, so this is a fact about the collector's own
# requests rather than something read out of a downloaded artifact.
AUTH_MODE="anonymous"
AUTH_MODE_REASON="collector sends no credentials; all GCS requests use the public unauthenticated API"

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
  --arg prowjob_url "$PROWJOB_URL" \
  --arg prowjob_path "$PROWJOB_PATH" \
  --arg prowjob_status "$PROWJOB_STATUS" \
  --arg clone_records_url "$CLONE_RECORDS_URL" \
  --arg clone_records_path "$CLONE_RECORDS_PATH" \
  --arg clone_records_status "$CLONE_RECORDS_STATUS" \
  --arg finished_url "$FINISHED_URL" \
  --arg finished_path "$FINISHED_PATH" \
  --arg finished_status "$FINISHED_STATUS" \
  --arg source_clone_sha "$SOURCE_CLONE_SHA" \
  --arg source_clone_sha_reason "$SOURCE_CLONE_SHA_REASON" \
  --arg source_clone_ref "$SOURCE_CLONE_REF" \
  --arg source_clone_ref_reason "$SOURCE_CLONE_REF_REASON" \
  --arg playwright_sha "$PLAYWRIGHT_SHA" \
  --arg playwright_sha_reason "$PLAYWRIGHT_SHA_REASON" \
  --arg job_result "$JOB_RESULT" \
  --arg job_result_reason "$JOB_RESULT_REASON" \
  --arg top_level_build_log_url "$TOP_LEVEL_BUILD_LOG_URL" \
  --arg top_level_build_log_path "$TOP_LEVEL_BUILD_LOG_PATH" \
  --arg top_level_build_log_status "$TOP_LEVEL_BUILD_LOG_STATUS" \
  --arg step_build_log_url "$BUILD_LOG_URL" \
  --arg step_build_log_path "$STEP_BUILD_LOG_PATH" \
  --arg step_build_log_status "$STEP_BUILD_LOG_STATUS" \
  --argjson junit "$JUNIT_RECORDS_JSON" \
  --argjson attachment_status_map "$ATTACHMENT_STATUS_MAP_JSON" \
  --argjson evidence_gaps "$EVIDENCE_GAPS_JSON" \
  --argjson builder_diagnostics "$BUILDER_DIAGNOSTICS_JSON" \
  --arg source_image_digest "$SOURCE_IMAGE_DIGEST" \
  --arg source_image_digest_reason "$SOURCE_IMAGE_DIGEST_REASON" \
  --arg release_config_revision "$RELEASE_CONFIG_REVISION" \
  --arg release_config_revision_reason "$RELEASE_CONFIG_REVISION_REASON" \
  --arg auth_mode "$AUTH_MODE" \
  --arg auth_mode_reason "$AUTH_MODE_REASON" \
  '
  def strip_ansi: if type == "string" then gsub("[[:cntrl:]]\\[[0-9;]*m"; "") else . end;
  def nullify: if . == "" then null else . end;
  def with_attachment_status:
    . as $a
    | (if $a.url != null then ($attachment_status_map[$a.url] // {status: null, reason: null})
       elif $a.body != null then {status: "inline", reason: "attachment body embedded in results.json"}
       else {status: "missing", reason: "no attachment path in results.json"} end) as $st
    | {name: $a.name, path: $a.path, url: $a.url} + $st;
  def build_attachments: [ .attachments[] | { name, path, body, url: (if .path then ('"$ATTACHMENT_URL_JQ"') else null end) } | with_attachment_status ];
  (.config.projects // []) as $projects
  | ([$projects[]?.metadata.actualWorkers] | map(select(. != null)) | first) as $project_actual_workers
  | (if $project_actual_workers != null then $project_actual_workers else .config.workers end) as $actual_workers
  | ([$projects[]?.retries] | map(select(. != null)) | max) as $retries
  | ([$projects[]?.use.trace] | map(select(. != null)) | first) as $configured_trace
  | ([.. | objects | select(has("attachments")) | .attachments[]? | select(.name == "trace")] | length) as $trace_attachment_count
  | (if $configured_trace != null then $configured_trace
     elif $trace_attachment_count > 0 then "traces captured on failing/retried attempts (inferred from \($trace_attachment_count) trace attachment(s) in results.json; config.projects[].use.trace not serialized)"
     else null end) as $tracing_value
  | [.. | objects | select(has("specs")) | .specs[]] as $specs
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
      top_level_build_log: { source_url: $top_level_build_log_url, local_path: ($top_level_build_log_path | nullify), status: $top_level_build_log_status },
      step_build_log: { source_url: $step_build_log_url, local_path: ($step_build_log_path | nullify), status: $step_build_log_status },
      prowjob: { source_url: $prowjob_url, local_path: ($prowjob_path | nullify), status: $prowjob_status },
      clone_records: { source_url: $clone_records_url, local_path: ($clone_records_path | nullify), status: $clone_records_status },
      finished: { source_url: $finished_url, local_path: ($finished_path | nullify), status: $finished_status },
      junit: $junit,
      provenance: {
        source_image_digest: { value: ($source_image_digest | nullify), reason: ($source_image_digest_reason | nullify) },
        release_config_revision: { value: ($release_config_revision | nullify), reason: ($release_config_revision_reason | nullify) },
        auth_mode: { value: $auth_mode, reason: $auth_mode_reason },
        actual_workers: { value: $actual_workers, reason: (if $project_actual_workers != null then null elif $actual_workers != null then "config.projects[].metadata.actualWorkers not present in results.json; using root config.workers" else "config.projects[].metadata.actualWorkers and root config.workers not present in results.json" end) },
        retries: { value: $retries, reason: (if $retries == null then "config.projects[].retries not present in results.json" else null end) },
        tracing_configuration: { value: $tracing_value, reason: (if $tracing_value == null then "no config.projects[].use.trace value and no trace attachments found in results.json" else null end) },
        source_clone_sha: { value: ($source_clone_sha | nullify), reason: ($source_clone_sha_reason | nullify) },
        source_clone_ref: { value: ($source_clone_ref | nullify), reason: ($source_clone_ref_reason | nullify) },
        playwright_sha: { value: ($playwright_sha | nullify), reason: ($playwright_sha_reason | nullify) },
        job_result: { value: ($job_result | nullify), reason: ($job_result_reason | nullify) }
      },
      has_container_logs: $has_container_logs,
      has_jaeger_traces: $has_jaeger_traces,
      container_log_files: $container_log_files,
      redacted_container_log_files: $redacted_container_log_files,
      jaeger_trace_files: $jaeger_trace_files,
      jaeger_artifact_base_url: $jaeger_artifact_base_url,
      evidence_gaps: $evidence_gaps,
      builder_diagnostics: $builder_diagnostics,
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
          attachments: build_attachments
        } ]
      } ],
      flaky: [ $specs[] as $s | $s.tests[] | select(.status == "flaky") | {
        title: $s.title, file: $s.file, line: $s.line,
        retries: ([.results[].retry] | max),
        first_error: ((.results[0].errors[0].message // .results[0].error.message // "") | strip_ansi),
        attempts: [ .results[] | {
          retry: .retry, status: .status, duration: .duration,
          errors: [ .errors[].message | strip_ansi ],
          attachments: build_attachments
        } ]
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
