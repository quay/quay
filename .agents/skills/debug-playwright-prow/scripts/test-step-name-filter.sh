#!/bin/bash
# test-step-name-filter.sh -- Unit tests for the nested-fallback step-name filter
# in playwright-debug-prow.sh.
#
# Verifies that the case-statement guard accepts only known Playwright step names
# and rejects unrelated step directories, matching the logic in the script.
#
# Run: bash .agents/skills/debug-playwright-prow/scripts/test-step-name-filter.sh
# Exit codes:
#   0 — all assertions passed
#   1 — one or more assertions failed

set -euo pipefail

PASS=0
FAIL=0

# step_name_matches mirrors the case statement in playwright-debug-prow.sh.
step_name_matches() {
  local candidate="$1"
  case "$candidate" in
    quay-test-e2e|e2e|e2e-test|quay-e2e) return 0 ;;
    *) return 1 ;;
  esac
}

assert_match() {
  local name="$1"
  if step_name_matches "$name"; then
    echo "PASS: '$name' is accepted"
    PASS=$(( PASS + 1 ))
  else
    echo "FAIL: '$name' should be accepted but was rejected"
    FAIL=$(( FAIL + 1 ))
  fi
}

assert_no_match() {
  local name="$1"
  if ! step_name_matches "$name"; then
    echo "PASS: '$name' is correctly rejected"
    PASS=$(( PASS + 1 ))
  else
    echo "FAIL: '$name' should be rejected but was accepted"
    FAIL=$(( FAIL + 1 ))
  fi
}

# --- Step-name acceptance tests ---
# All names from the primary discovery loop must be accepted.
assert_match "quay-test-e2e"
assert_match "e2e"
assert_match "e2e-test"
assert_match "quay-e2e"

# --- Rejection tests ---
# Unrelated step directories that might also upload results.json should
# never be selected as the Playwright artifact source.
assert_no_match "unrelated-step"
assert_no_match "gather-extra"
assert_no_match "quay-gather-jaeger-traces"
assert_no_match "ipi-install"
assert_no_match "e2e-other"
assert_no_match "quay-test"
assert_no_match ""

# --- Step-name extraction from GCS prefix paths ---
# The script extracts the step name with:
#   candidate="${stepdir%/}"
#   candidate="${candidate##*/}"
# Verify that extraction produces the expected leaf name for real GCS prefixes.

extract_candidate() {
  local stepdir="$1"
  local c
  c="${stepdir%/}"
  c="${c##*/}"
  printf '%s' "$c"
}

assert_extracted() {
  local stepdir="$1"
  local expected="$2"
  local actual
  actual="$(extract_candidate "$stepdir")"
  if test "$actual" = "$expected"; then
    echo "PASS: extract '$stepdir' -> '$actual'"
    PASS=$(( PASS + 1 ))
  else
    echo "FAIL: extract '$stepdir': expected '$expected', got '$actual'"
    FAIL=$(( FAIL + 1 ))
  fi
}

# Playwright step in a nested layout — should be accepted.
assert_extracted "logs/job/12345/artifacts/e2e-workflow/quay-test-e2e/" "quay-test-e2e"
assert_extracted "logs/job/12345/artifacts/e2e-workflow/e2e/" "e2e"
assert_extracted "logs/job/12345/artifacts/e2e-workflow/e2e-test/" "e2e-test"
assert_extracted "logs/job/12345/artifacts/e2e-workflow/quay-e2e/" "quay-e2e"

# Unrelated step in the same workflow — should be rejected.
assert_extracted "logs/job/12345/artifacts/e2e-workflow/unrelated-step/" "unrelated-step"
assert_extracted "logs/job/12345/artifacts/e2e-workflow/gather-extra/" "gather-extra"

# --- Two-directory fixture: Playwright step wins, unrelated step is skipped ---
# Simulates the multi-step layout described in the issue:
#   unrelated-step/artifacts/results.json   -> must not be selected
#   quay-test-e2e/artifacts/results.json    -> must be selected

simulate_nested_fallback() {
  local selected=""
  # Tracks how many simulated HEAD probes occurred (only reached for accepted names).
  local probe_count=0
  # Directories as the GCS XML listing returns them (both contain results.json).
  local step_dirs="logs/job/12345/artifacts/e2e-workflow/unrelated-step/ logs/job/12345/artifacts/e2e-workflow/quay-test-e2e/"
  for stepdir in $step_dirs; do
    local _candidate
    _candidate="${stepdir%/}"
    _candidate="${_candidate##*/}"
    case "$_candidate" in
      quay-test-e2e|e2e|e2e-test|quay-e2e) ;;
      # Filtered out — no HEAD probe is issued; continue to next directory.
      *) continue ;;
    esac
    # Simulate a successful HEAD probe (only accepted step names reach here).
    probe_count=$(( probe_count + 1 ))
    selected="$_candidate"
    break
  done
  printf '%d %s' "$probe_count" "$selected"
}

fixture_result="$(simulate_nested_fallback)"
fixture_probed="${fixture_result%% *}"
fixture_selected="${fixture_result##* }"

# Exactly one HEAD probe should be made — for the accepted quay-test-e2e step.
# The unrelated-step directory must be skipped before any probe is issued.
if test "$fixture_probed" -eq 1; then
  echo "PASS: exactly 1 HEAD probe made (unrelated-step filtered, quay-test-e2e probed)"
  PASS=$(( PASS + 1 ))
else
  echo "FAIL: expected 1 HEAD probe, got ${fixture_probed}"
  FAIL=$(( FAIL + 1 ))
fi

if test "$fixture_selected" = "quay-test-e2e"; then
  echo "PASS: quay-test-e2e was selected as the Playwright step"
  PASS=$(( PASS + 1 ))
else
  echo "FAIL: expected 'quay-test-e2e' to be selected, got '${fixture_selected}'"
  FAIL=$(( FAIL + 1 ))
fi

# --- Summary ---
echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"
test "$FAIL" -eq 0
