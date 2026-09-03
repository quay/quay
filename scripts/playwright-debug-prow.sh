#!/bin/bash
# playwright-debug-prow.sh -- Download and analyze Playwright CI artifacts from Prow/OpenShift CI.
#
# Usage:
#   bash scripts/playwright-debug-prow.sh <PROW_URL>
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
MAX_XML_BYTES=52428800                   # 50 MiB cap on JUnit XML before parsing

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
JOB_START=$(echo "$PROWJOB_JSON" | jq -r '.status.startTime // ""')
JOB_COMPLETION=$(echo "$PROWJOB_JSON" | jq -r '.status.completionTime // ""')

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
# We try common step names.
STEP_NAME="quay-test-e2e"

# Discover the workflow name by listing artifact directories.
# The workflow name is the first directory under artifacts/.
# We'll try to download the JUnit XML to confirm the path.
WORK_DIR=$(mktemp -d)
echo "Downloading artifacts to $WORK_DIR ..." >&2

# Try to find the correct artifact path by probing for junit_playwright.xml
JUNIT_FOUND=false
ARTIFACT_BASE=""

# Build a list of candidate artifact base paths to probe.
# The structure is: artifacts/{workflow_name}/{step_name}/artifacts/
# We try the step name directly under common workflow patterns.
# First, try fetching the started.json to get more context
STARTED_JSON=$(curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" "${GCS_BASE}/started.json" 2>/dev/null || echo "{}")

# Probe for JUnit XML at the expected artifact paths
# Pattern: artifacts/{workflow}/{step}/artifacts/junit_playwright.xml
for step in "$STEP_NAME" "e2e" "e2e-test" "quay-e2e"; do
  PROBE_URL="${GCS_BASE}/artifacts/${step}/artifacts/junit_playwright.xml"
  if curl -sfL "${CURL_TIMEOUT[@]}" --head "$PROBE_URL" >/dev/null 2>&1; then
    ARTIFACT_BASE="${GCS_BASE}/artifacts/${step}/artifacts"
    STEP_NAME="$step"
    JUNIT_FOUND=true
    echo "  Found artifacts at: artifacts/${step}/artifacts/" >&2
    break
  fi

  # Also try with a workflow name prefix (artifacts/workflow/step/artifacts/)
  # Common pattern: the job name contains the workflow info
  # Try without the workflow prefix as some jobs put artifacts directly
  PROBE_URL="${GCS_BASE}/artifacts/${step}/junit_playwright.xml"
  if curl -sfL "${CURL_TIMEOUT[@]}" --head "$PROBE_URL" >/dev/null 2>&1; then
    ARTIFACT_BASE="${GCS_BASE}/artifacts/${step}"
    STEP_NAME="$step"
    JUNIT_FOUND=true
    echo "  Found artifacts at: artifacts/${step}/ (flat layout)" >&2
    break
  fi
done

# If not found with simple names, try a broader search using the GCS XML API
if [ "$JUNIT_FOUND" != "true" ]; then
  echo "  Probing GCS for junit_playwright.xml location..." >&2
  # Use the GCS XML API to list objects with a prefix filter
  GCS_LIST_URL="https://storage.googleapis.com/${GCS_BUCKET}?prefix=${GCS_JOB_PATH}/${BUILD_ID}/artifacts/&delimiter=/"
  ARTIFACT_DIRS=$(curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" "$GCS_LIST_URL" 2>/dev/null | grep -oP '(?<=<Prefix>)[^<]+' || true)

  for dir in $ARTIFACT_DIRS; do
    # dir looks like: logs/JOB_NAME/BUILD_ID/artifacts/WORKFLOW_NAME/
    WORKFLOW_DIR=$(basename "$dir")
    PROBE_URL="https://storage.googleapis.com/${GCS_BUCKET}/${dir}${STEP_NAME}/artifacts/junit_playwright.xml"
    if curl -sfL "${CURL_TIMEOUT[@]}" --head "$PROBE_URL" >/dev/null 2>&1; then
      ARTIFACT_BASE="https://storage.googleapis.com/${GCS_BUCKET}/${dir}${STEP_NAME}/artifacts"
      JUNIT_FOUND=true
      echo "  Found artifacts at: ${dir}${STEP_NAME}/artifacts/" >&2
      break
    fi
  done
fi

if [ "$JUNIT_FOUND" != "true" ]; then
  echo "ERROR: Could not locate junit_playwright.xml in artifacts" >&2
  echo "  Tried step names: $STEP_NAME, e2e, e2e-test, quay-e2e" >&2
  echo "  Check the job artifacts at: ${GCSWEB_BASE}/artifacts/" >&2
  exit 1
fi

# --- Download Artifacts ---
HAS_JUNIT=false
HAS_PLAYWRIGHT_LOG=false
HAS_BUILD_LOG=false
HAS_HTML_REPORT=false
HAS_CONTAINER_LOGS=false

# Download JUnit XML
curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" "${ARTIFACT_BASE}/junit_playwright.xml" -o "$WORK_DIR/junit_playwright.xml" 2>/dev/null && {
  HAS_JUNIT=true
  echo "  Downloaded: junit_playwright.xml" >&2
} || echo "  Warning: failed to download junit_playwright.xml" >&2

# Download Playwright output log
curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" "${ARTIFACT_BASE}/playwright-output.log" -o "$WORK_DIR/playwright-output.log" 2>/dev/null && {
  HAS_PLAYWRIGHT_LOG=true
  echo "  Downloaded: playwright-output.log" >&2
} || echo "  Not available: playwright-output.log" >&2

# Download build log (one level up from artifacts/)
BUILD_LOG_URL="${ARTIFACT_BASE%/artifacts}/build-log.txt"
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

# Check for container logs in gather-extra artifacts
# Pattern: artifacts/{workflow}/gather-extra/artifacts/...
# GCS has a flat namespace: slash-delimited "folders" are simulated prefixes, so
# a HEAD on "${GATHER_EXTRA_BASE}/" can 404 even when logs exist under it. Probe
# the candidate log objects directly instead of gating on a directory request.
GATHER_EXTRA_BASE="${ARTIFACT_BASE%/${STEP_NAME}/artifacts}/gather-extra/artifacts"
mkdir -p "$WORK_DIR/container-logs"
# Probe for common quay pod log locations
for log_name in "quay-quay.log" "quay.log" "pods/quay.log"; do
  if curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" "${GATHER_EXTRA_BASE}/${log_name}" -o "$WORK_DIR/container-logs/quay.log" 2>/dev/null; then
    HAS_CONTAINER_LOGS=true
    echo "  Downloaded: container logs (${log_name})" >&2
    break
  fi
done
if [ "$HAS_CONTAINER_LOGS" != "true" ]; then
  rmdir "$WORK_DIR/container-logs" 2>/dev/null || true
  echo "  Not available: container logs (no quay pod logs under gather-extra)" >&2
fi

# --- Parse JUnit XML ---
if [ "$HAS_JUNIT" != "true" ]; then
  echo "ERROR: JUnit XML is required for analysis" >&2
  exit 1
fi

# Use Python to parse JUnit XML — more reliable than xmlstarlet and usually available
PARSE_RESULT=$(python3 -c '
import xml.etree.ElementTree as ET
import json
import os
import re
import sys

xml_path = sys.argv[1]
max_bytes = int(sys.argv[2])

# Bound the parse: refuse an oversized JUnit XML before loading it into memory.
try:
    size = os.path.getsize(xml_path)
except OSError as e:
    print(json.dumps({"parse_error": str(e)}))
    sys.exit(0)
if size > max_bytes:
    print(json.dumps({"parse_error": "junit_playwright.xml is %d bytes, exceeds cap of %d" % (size, max_bytes)}))
    sys.exit(0)

try:
    tree = ET.parse(xml_path)
except ET.ParseError as e:
    print(json.dumps({"parse_error": str(e)}))
    sys.exit(0)

root = tree.getroot()

# Playwright error text carries the source location as "<spec>.spec.ts:<line>:<col>".
LOC_RE = re.compile(r"([\w./-]+\.spec\.ts):(\d+)")

def source_line(tc, *texts):
    # Prefer an explicit line attribute; otherwise scrape the error text.
    line = tc.get("line", "")
    if line:
        return line
    for text in texts:
        m = LOC_RE.search(text or "")
        if m:
            return m.group(2)
    return ""

stats = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "interrupted": 0,
    "flaky": 0,
    "duration": 0.0
}

failed = []
flaky = []
interrupted = []

# Handle both <testsuites> and <testsuite> as root
suites = root.findall(".//testsuite") if root.tag == "testsuites" else [root]

for suite in suites:
    suite_name = suite.get("name", "")
    stats["total"] += int(suite.get("tests", "0"))
    stats["skipped"] += int(suite.get("skipped", "0"))
    try:
        stats["duration"] += float(suite.get("time", "0"))
    except ValueError:
        pass

    for tc in suite.findall("testcase"):
        tc_name = tc.get("name", "")
        tc_classname = tc.get("classname", "")
        tc_file = tc.get("file", tc_classname)
        tc_time = tc.get("time", "0")

        failure = tc.find("failure")
        error = tc.find("error")
        skipped = tc.find("skipped")

        if failure is not None:
            error_msg = failure.get("message", "")
            error_text = (failure.text or "")[:2000]
            failed.append({
                "title": tc_name,
                "file": tc_file,
                "line": source_line(tc, error_text, error_msg),
                "suite": suite_name,
                "duration": tc_time,
                "error_message": error_msg[:500],
                "error_detail": error_text,
            })
        elif error is not None:
            error_msg = error.get("message", "")
            error_text = (error.text or "")[:2000]
            # Interrupted tests usually have "interrupted" in the message
            if "interrupt" in error_msg.lower():
                interrupted.append({
                    "title": tc_name,
                    "file": tc_file,
                    "suite": suite_name,
                })
            else:
                failed.append({
                    "title": tc_name,
                    "file": tc_file,
                    "line": source_line(tc, error_text, error_msg),
                    "suite": suite_name,
                    "duration": tc_time,
                    "error_message": error_msg[:500],
                    "error_detail": error_text,
                })

# Derive summary counts from the final classifications rather than the raw
# suite attributes: a <testcase> carrying <error> lands in failed/interrupted
# but is not reflected in the suite "failures" count.
stats["failed"] = len(failed)
stats["interrupted"] = len(interrupted)
stats["passed"] = max(stats["total"] - stats["failed"] - stats["interrupted"] - stats["skipped"], 0)

print(json.dumps({
    "stats": stats,
    "failed": failed,
    "flaky": flaky,
    "interrupted": interrupted,
}, indent=2))
' "$WORK_DIR/junit_playwright.xml" "$MAX_XML_BYTES" 2>/dev/null) || {
  echo "ERROR: Failed to parse JUnit XML" >&2
  exit 1
}

# Check for parse error
PARSE_ERROR=$(echo "$PARSE_RESULT" | jq -r '.parse_error // empty')
if [ -n "$PARSE_ERROR" ]; then
  echo "ERROR: JUnit XML parse error: $PARSE_ERROR" >&2
  exit 1
fi

STATS=$(echo "$PARSE_RESULT" | jq '.stats')
FAILED=$(echo "$PARSE_RESULT" | jq '.failed')
FLAKY=$(echo "$PARSE_RESULT" | jq '.flaky')
INTERRUPTED=$(echo "$PARSE_RESULT" | jq '.interrupted')

FAILED_COUNT=$(echo "$FAILED" | jq 'length')

# --- Detect Flaky Tests from Playwright Output Log ---
# The playwright output log may contain retry information that the JUnit XML lacks.
# If we have the log, look for "retry #N" patterns to identify flaky tests.
if [ "$HAS_PLAYWRIGHT_LOG" = "true" ]; then
  FLAKY_FROM_LOG=$(python3 -c '
import json, re, sys

flaky = []
seen = set()
retry_pattern = re.compile(r"\[retry #(\d+)\]")
file_pattern = re.compile(r"([\w./-]+\.spec\.ts)")

with open(sys.argv[1]) as f:
    for line in f:
        m = retry_pattern.search(line)
        if m and "passed" in line.lower():
            # Extract test name from lines like: "[retry #1] ... test-name ... passed"
            parts = line.strip()
            if parts not in seen:
                seen.add(parts)
                fm = file_pattern.search(parts)
                flaky.append({
                    "title": parts,
                    "file": fm.group(1) if fm else "",
                    "retries": int(m.group(1)),
                })

print(json.dumps(flaky))
' "$WORK_DIR/playwright-output.log" 2>/dev/null || echo "[]")

  FLAKY_COUNT=$(echo "$FLAKY_FROM_LOG" | jq 'length')
  if [ "$FLAKY_COUNT" -gt 0 ]; then
    FLAKY="$FLAKY_FROM_LOG"
    # Keep the summary count in sync with the classified flaky list.
    STATS=$(echo "$STATS" | jq --argjson n "$FLAKY_COUNT" '.flaky = $n')
    echo "  Detected $FLAKY_COUNT flaky test(s) from playwright output log" >&2
  fi
fi

# --- Enrich Failed Tests with Context from Playwright Log ---
# Search the playwright output log for additional context on each failure.
if [ "$HAS_PLAYWRIGHT_LOG" = "true" ] && [ "$FAILED_COUNT" -gt 0 ]; then
  FAILED=$(python3 -c '
import json, sys

failed = json.loads(sys.argv[1])
log_file = sys.argv[2]

with open(log_file) as f:
    log_lines = f.readlines()

log_text = "".join(log_lines)

for test in failed:
    title = test.get("title", "")
    # Find the last Playwright action before the error (similar to last_step in GHA)
    context_lines = []
    in_test = False
    for i, line in enumerate(log_lines):
        if title in line:
            in_test = True
            context_lines = []
        elif in_test:
            stripped = line.strip()
            if stripped.startswith("locator.") or stripped.startswith("page.") or stripped.startswith("expect("):
                test["last_step"] = stripped[:200]
            if "Error:" in line or "Timeout" in line:
                context_lines.append(stripped[:300])
                # Grab a few lines after the error
                for j in range(i+1, min(i+4, len(log_lines))):
                    context_lines.append(log_lines[j].strip()[:300])
                break

    if context_lines:
        test["error_context"] = "\n".join(context_lines)

print(json.dumps(failed))
' "$FAILED" "$WORK_DIR/playwright-output.log" 2>/dev/null) || true
fi

# --- Check for Global Setup Failure ---
GLOBAL_SETUP_FAILURE=false
SETUP_ERRORS="[]"
TOTAL_TESTS=$(echo "$STATS" | jq '.total')

if [ "$TOTAL_TESTS" -eq 0 ]; then
  GLOBAL_SETUP_FAILURE=true
  # Try to extract setup errors from build log
  if [ "$HAS_BUILD_LOG" = "true" ]; then
    SETUP_ERRORS=$(grep -i "error\|fatal\|failed" "$WORK_DIR/build-log.txt" | tail -20 | \
      python3 -c 'import json,sys; print(json.dumps([l.strip()[:500] for l in sys.stdin.readlines()]))' 2>/dev/null || echo "[]")
  fi
fi

# --- Build Report URLs ---
HTML_REPORT_GCSWEB=""
if [ "$HAS_HTML_REPORT" = "true" ]; then
  # Convert GCS URL to GCSWeb URL for browsable access
  ARTIFACT_PATH="${ARTIFACT_BASE#https://storage.googleapis.com/}"
  HTML_REPORT_GCSWEB="https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/${ARTIFACT_PATH}/index.html"
fi

# --- Output ---
jq -n \
  --arg build_id "$BUILD_ID" \
  --arg job_name "$JOB_NAME" \
  --arg prow_url "$PROW_URL" \
  --arg gcsweb_url "$GCSWEB_BASE" \
  --arg job_status "$JOB_STATUS" \
  --arg artifacts_dir "$WORK_DIR" \
  --arg artifact_base_url "$ARTIFACT_BASE" \
  --arg html_report_url "$HTML_REPORT_GCSWEB" \
  --argjson has_playwright_log "$HAS_PLAYWRIGHT_LOG" \
  --argjson has_build_log "$HAS_BUILD_LOG" \
  --argjson has_container_logs "$HAS_CONTAINER_LOGS" \
  --argjson has_jaeger_traces false \
  --argjson global_setup_failure "$GLOBAL_SETUP_FAILURE" \
  --argjson stats "$STATS" \
  --argjson failed "$FAILED" \
  --argjson flaky "$FLAKY" \
  --argjson interrupted "$INTERRUPTED" \
  --argjson setup_errors "$SETUP_ERRORS" \
  '{
    build_id: $build_id,
    job_name: $job_name,
    prow_url: $prow_url,
    gcsweb_url: $gcsweb_url,
    job_status: $job_status,
    artifacts_dir: $artifacts_dir,
    artifact_base_url: $artifact_base_url,
    html_report_url: $html_report_url,
    has_playwright_log: $has_playwright_log,
    has_build_log: $has_build_log,
    has_container_logs: $has_container_logs,
    has_jaeger_traces: $has_jaeger_traces,
    global_setup_failure: $global_setup_failure,
    stats: $stats,
    failed: $failed,
    flaky: $flaky,
    interrupted: $interrupted,
    setup_errors: $setup_errors
  }'
