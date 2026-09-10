#!/bin/bash
# test_gather_extra_base.sh -- Unit tests for GATHER_EXTRA_BASE path derivation.
#
# Verifies that the two-step suffix strip resolves the correct sibling
# gather-extra/artifacts path for both Prow artifact-layout shapes.
#
# Usage:
#   bash .agents/skills/debug-playwright-prow/scripts/test_gather_extra_base.sh
#
# Exit codes:
#   0 — all tests passed
#   1 — one or more tests failed

set -euo pipefail

PASS=0
FAIL=0

assert_eq() {
  local test_name="$1"
  local expected="$2"
  local actual="$3"
  if [ "$expected" = "$actual" ]; then
    echo "PASS: ${test_name}"
    PASS=$(( PASS + 1 ))
  else
    echo "FAIL: ${test_name}"
    echo "      expected: ${expected}"
    echo "      actual:   ${actual}"
    FAIL=$(( FAIL + 1 ))
  fi
}

# Replicate the GATHER_EXTRA_BASE derivation from playwright-debug-prow.sh.
derive_gather_extra_base() {
  local artifact_base="$1"
  local step_name="$2"
  local workflow_base
  workflow_base="${artifact_base%/artifacts}"
  workflow_base="${workflow_base%"/${step_name}"}"
  echo "${workflow_base}/gather-extra/artifacts"
}

# --- Test: normal Prow layout ---
# ARTIFACT_BASE = GCS_BASE/artifacts/STEP_NAME/artifacts
# Expected GATHER_EXTRA_BASE = GCS_BASE/artifacts/gather-extra/artifacts
GCS_BASE="https://storage.googleapis.com/test-bucket/logs/test-job/1234567890"
STEP_NAME="quay-test-e2e"

ARTIFACT_BASE="${GCS_BASE}/artifacts/${STEP_NAME}/artifacts"
EXPECTED="${GCS_BASE}/artifacts/gather-extra/artifacts"
ACTUAL=$(derive_gather_extra_base "$ARTIFACT_BASE" "$STEP_NAME")
assert_eq "normal layout (quay-test-e2e)" "$EXPECTED" "$ACTUAL"

# Normal layout with a workflow prefix directory
# Some Prow runs nest steps under a workflow directory:
#   artifacts/WORKFLOW/STEP_NAME/artifacts/
ARTIFACT_BASE="${GCS_BASE}/artifacts/workflow/${STEP_NAME}/artifacts"
EXPECTED="${GCS_BASE}/artifacts/workflow/gather-extra/artifacts"
ACTUAL=$(derive_gather_extra_base "$ARTIFACT_BASE" "$STEP_NAME")
assert_eq "normal layout (workflow-prefixed)" "$EXPECTED" "$ACTUAL"

# --- Test: flat Prow layout ---
# ARTIFACT_BASE = GCS_BASE/artifacts/STEP_NAME  (no trailing /artifacts)
# Expected GATHER_EXTRA_BASE = GCS_BASE/artifacts/gather-extra/artifacts
ARTIFACT_BASE="${GCS_BASE}/artifacts/${STEP_NAME}"
EXPECTED="${GCS_BASE}/artifacts/gather-extra/artifacts"
ACTUAL=$(derive_gather_extra_base "$ARTIFACT_BASE" "$STEP_NAME")
assert_eq "flat layout (quay-test-e2e)" "$EXPECTED" "$ACTUAL"

# --- Test: flat layout with alternate step name ---
STEP_NAME="e2e"
ARTIFACT_BASE="${GCS_BASE}/artifacts/${STEP_NAME}"
EXPECTED="${GCS_BASE}/artifacts/gather-extra/artifacts"
ACTUAL=$(derive_gather_extra_base "$ARTIFACT_BASE" "$STEP_NAME")
assert_eq "flat layout (e2e)" "$EXPECTED" "$ACTUAL"

# --- Test: normal layout with alternate step name ---
ARTIFACT_BASE="${GCS_BASE}/artifacts/${STEP_NAME}/artifacts"
EXPECTED="${GCS_BASE}/artifacts/gather-extra/artifacts"
ACTUAL=$(derive_gather_extra_base "$ARTIFACT_BASE" "$STEP_NAME")
assert_eq "normal layout (e2e)" "$EXPECTED" "$ACTUAL"

# --- Summary ---
echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"
if [ "$FAIL" -ne 0 ]; then
  exit 1
fi
