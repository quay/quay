#!/usr/bin/env bash
# test-results-json-validation.sh -- Unit tests for results.json shape validation.
#
# Tests the jq shape-validation expression used in playwright-debug-prow.sh to
# reject results.json files that are syntactically valid JSON but lack the
# expected top-level Playwright reporter keys (stats, suites, results).
#
# Usage:
#   bash .agents/skills/debug-playwright-prow/scripts/tests/test-results-json-validation.sh
#
# Exit codes:
#   0 — all tests passed
#   1 — one or more tests failed

set -euo pipefail

PASS=0
FAIL=0

# The shape-validation expression extracted from playwright-debug-prow.sh.
SHAPE_CHECK='type == "object" and (has("stats") or has("suites") or has("results"))'

# assert_shape_fails <label> <json>
#   Asserts that the jq shape check rejects the given JSON (exit non-zero).
assert_shape_fails() {
  local label="$1"
  local json="$2"
  if echo "$json" | jq -e "$SHAPE_CHECK" >/dev/null 2>&1; then
    echo "FAIL: $label — shape check passed but expected rejection" >&2
    FAIL=$(( FAIL + 1 ))
  else
    echo "PASS: $label"
    PASS=$(( PASS + 1 ))
  fi
}

# assert_shape_passes <label> <json>
#   Asserts that the jq shape check accepts the given JSON (exit zero).
assert_shape_passes() {
  local label="$1"
  local json="$2"
  if echo "$json" | jq -e "$SHAPE_CHECK" >/dev/null 2>&1; then
    echo "PASS: $label"
    PASS=$(( PASS + 1 ))
  else
    echo "FAIL: $label — shape check rejected but expected acceptance" >&2
    FAIL=$(( FAIL + 1 ))
  fi
}

# assert_invalid_json <label> <json>
#   Asserts that the syntax check (jq -e .) rejects the given input (exit non-zero).
assert_invalid_json() {
  local label="$1"
  local json="$2"
  if echo "$json" | jq -e . >/dev/null 2>&1; then
    echo "FAIL: $label — syntax check passed but expected rejection" >&2
    FAIL=$(( FAIL + 1 ))
  else
    echo "PASS: $label"
    PASS=$(( PASS + 1 ))
  fi
}

echo "--- Syntax validation (jq -e .) ---"
assert_invalid_json "truncated JSON rejects" '{"stats": {'
assert_invalid_json "bare string rejects" 'not json at all'

echo ""
echo "--- Shape validation: reject cases ---"
assert_shape_fails "empty object {}" '{}'
assert_shape_fails "array [] rejects" '[]'
assert_shape_fails "object missing all expected keys" '{"foo": 1}'
assert_shape_fails "object with unrelated nested stats" '{"data": {"stats": {}}}'

echo ""
echo "--- Shape validation: accept cases ---"
assert_shape_passes "object with stats key" '{"stats": {}}'
assert_shape_passes "object with suites key" '{"suites": []}'
assert_shape_passes "object with results key" '{"results": []}'
assert_shape_passes "object with all three keys" '{"stats": {}, "suites": [], "results": []}'
assert_shape_passes "object with stats and extra keys" '{"stats": {"expected": 10}, "errors": []}'

echo ""
echo "--- Summary ---"
echo "Passed: $PASS  Failed: $FAIL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
