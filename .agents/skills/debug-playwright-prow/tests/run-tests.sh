#!/bin/bash
# run-tests.sh -- plain bash test runner for collector-lib.sh. No test
# framework dependency: bash + jq only, matching the collector itself.
#
# Usage:
#   bash .agents/skills/debug-playwright-prow/tests/run-tests.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../scripts/collector-lib.sh
. "$SCRIPT_DIR/../scripts/collector-lib.sh"

FAIL_COUNT=0

assert_eq() {
  local expected="$1" actual="$2" msg="$3"
  if [ "$expected" != "$actual" ]; then
    echo "  assert_eq failed: $msg (expected '$expected', got '$actual')" >&2
    return 1
  fi
}

run_test() {
  # Subshell: isolates each test's global mutations (e.g. the MOCK_* vars
  # below) so a later test can't silently inherit an earlier test's state.
  if ("$1"); then
    echo "PASS: $1"
  else
    echo "FAIL: $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

PLACEHOLDER='This file contained potentially sensitive information and has been removed.'

# --- classify_bytes (requirement 1) ---

test_classify_bytes_placeholder_alone() {
  assert_eq "redacted" "$(classify_bytes "$PLACEHOLDER")" "placeholder alone"
}

test_classify_bytes_ordinary_content() {
  assert_eq "usable" "$(classify_bytes "an ordinary log line")" "ordinary content"
}

test_classify_bytes_large_first_line_placeholder() {
  local big
  big="${PLACEHOLDER}"$'\n'"$(printf '%*s' 10485760 '')"
  if [ "$(classify_bytes "$big")" = "redacted" ]; then
    return 0
  fi
  return 1
}

test_classify_bytes_large_no_placeholder() {
  local big
  big="$(printf '%*s' 10485760 '')"
  if [ "$(classify_bytes "$big")" = "usable" ]; then
    return 0
  fi
  return 1
}

# --- classify_object_head (requirement 2), curl shadowed ---

# Consumed by classify_object_head in the sourced lib, not in this file.
# shellcheck disable=SC2034
CURL_TIMEOUT=()
# shellcheck disable=SC2034
CURL_MAXSIZE=()
MOCK_HTTP_CODE=""
MOCK_RANGE_FAILS="false"
MOCK_RANGE_BODY=""

curl() {
  local a is_head=false
  for a in "$@"; do
    [ "$a" = "--head" ] && is_head=true
  done
  if [ "$is_head" = "true" ]; then
    printf '%s' "$MOCK_HTTP_CODE"
    return 0
  fi
  if [ "$MOCK_RANGE_FAILS" = "true" ]; then
    return 1
  fi
  printf '%s' "$MOCK_RANGE_BODY"
}

test_classify_object_head_404() {
  MOCK_HTTP_CODE="404"
  assert_eq "not_found" "$(classify_object_head "http://x")" "HEAD 404"
}

test_classify_object_head_403() {
  MOCK_HTTP_CODE="403"
  assert_eq "head_failed" "$(classify_object_head "http://x")" "HEAD 403"
}

test_classify_object_head_500() {
  MOCK_HTTP_CODE="500"
  assert_eq "head_failed" "$(classify_object_head "http://x")" "HEAD 500"
}

test_classify_object_head_redacted_body() {
  MOCK_HTTP_CODE="200"
  MOCK_RANGE_FAILS="false"
  MOCK_RANGE_BODY="$PLACEHOLDER"
  assert_eq "redacted" "$(classify_object_head "http://x")" "200 with placeholder range body"
}

test_classify_object_head_usable_body() {
  MOCK_HTTP_CODE="200"
  MOCK_RANGE_FAILS="false"
  MOCK_RANGE_BODY="intact bytes"
  assert_eq "usable" "$(classify_object_head "http://x")" "200 with intact range body"
}

test_classify_object_head_range_read_fails() {
  MOCK_HTTP_CODE="200"
  MOCK_RANGE_FAILS="true"
  assert_eq "missing" "$(classify_object_head "http://x")" "200 but range read fails"
}

# Exercises the actual status->gap emission logic used at the must-gather
# call site in playwright-debug-prow.sh's "Run-level Evidence Gaps" section,
# not a mirrored table.
test_must_gather_gap_record_usable() {
  assert_eq "" "$(must_gather_gap_record "usable" "http://x")" "usable produces no record"
}

test_must_gather_gap_record_not_found() {
  assert_eq "" "$(must_gather_gap_record "not_found" "http://x")" "not_found produces no record"
}

test_must_gather_gap_record_redacted() {
  local out
  out=$(must_gather_gap_record "redacted" "http://x")
  assert_eq "redacted" "$(printf '%s' "$out" | jq -r '.status')" "redacted status field" &&
    assert_eq "CI sensitive-content placeholder" "$(printf '%s' "$out" | jq -r '.reason')" "redacted reason field"
}

test_must_gather_gap_record_missing() {
  local out
  out=$(must_gather_gap_record "missing" "http://x")
  assert_eq "missing" "$(printf '%s' "$out" | jq -r '.status')" "missing status field" &&
    assert_eq "range read failed" "$(printf '%s' "$out" | jq -r '.reason')" "missing reason field"
}

test_must_gather_gap_record_head_failed() {
  local out
  out=$(must_gather_gap_record "head_failed" "http://x")
  assert_eq "missing" "$(printf '%s' "$out" | jq -r '.status')" "head_failed status field" &&
    assert_eq "HEAD probe failed" "$(printf '%s' "$out" | jq -r '.reason')" "head_failed reason field"
}

# --- is_safe_flat_name (requirement 3) ---

test_is_safe_flat_name_refuses() {
  local n
  for n in ".." "." "../../etc/passwd" "a/b" "x..y/../z" "name with space" 'name$var'; do
    if is_safe_flat_name "$n"; then
      echo "  expected refusal for: $n" >&2
      return 1
    fi
  done
}

test_is_safe_flat_name_accepts() {
  local n
  for n in "build-log.txt" "a_b-c.1"; do
    if ! is_safe_flat_name "$n"; then
      echo "  expected acceptance for: $n" >&2
      return 1
    fi
  done
}

test_is_safe_flat_name_path_escape_consequence() {
  local dest_dir="/tmp/safe-dest" name="../../etc/passwd"
  # A refused name must gate off before "$dest_dir/$name" is ever used to
  # write a file, since that path would resolve outside dest_dir.
  if is_safe_flat_name "$name"; then
    echo "  gate accepted a name that would escape $dest_dir" >&2
    return 1
  fi
}

# --- parse_playwright_sha (requirement 4) ---

TEST_TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEST_TMP_DIR"' EXIT

test_parse_playwright_sha_valid_line() {
  local f="$TEST_TMP_DIR/valid.log"
  printf 'PLAYWRIGHT_SOURCE_PROVENANCE repo=quay/quay ref=master sha=abc123\n' >"$f"
  parse_playwright_sha "$f"
  assert_eq "abc123" "$PLAYWRIGHT_SHA" "valid line sha" &&
    assert_eq "" "$PLAYWRIGHT_SHA_REASON" "valid line reason is empty"
}

test_parse_playwright_sha_unknown() {
  local f="$TEST_TMP_DIR/unknown.log"
  printf 'PLAYWRIGHT_SOURCE_PROVENANCE repo=quay/quay ref=master sha=unknown\n' >"$f"
  parse_playwright_sha "$f"
  assert_eq "" "$PLAYWRIGHT_SHA" "sha=unknown leaves PLAYWRIGHT_SHA empty" &&
    assert_eq "step printed sha=unknown (archive fallback, no git metadata)" "$PLAYWRIGHT_SHA_REASON" "sha=unknown reason"
}

test_parse_playwright_sha_unparseable_order() {
  local f="$TEST_TMP_DIR/unparseable.log"
  printf 'PLAYWRIGHT_SOURCE_PROVENANCE sha=abc123 ref=master repo=quay/quay\n' >"$f"
  parse_playwright_sha "$f"
  assert_eq "PLAYWRIGHT_SOURCE_PROVENANCE line present but repo=/ref=/sha= fields could not be parsed in order" "$PLAYWRIGHT_SHA_REASON" "out-of-order fields reason"
}

test_parse_playwright_sha_no_provenance_line() {
  local f="$TEST_TMP_DIR/no-provenance.log"
  printf 'some unrelated build output\nmore lines\n' >"$f"
  parse_playwright_sha "$f"
  assert_eq "step build log has no PLAYWRIGHT_SOURCE_PROVENANCE line (this CI step predates it)" "$PLAYWRIGHT_SHA_REASON" "no provenance line reason"
}

test_parse_playwright_sha_absent_path() {
  parse_playwright_sha ""
  assert_eq "step build log was not downloaded" "$PLAYWRIGHT_SHA_REASON" "absent path reason"
}

test_parse_playwright_sha_reasons_pairwise_distinct() {
  local f_unknown="$TEST_TMP_DIR/d-unknown.log"
  local f_unparseable="$TEST_TMP_DIR/d-unparseable.log"
  local f_none="$TEST_TMP_DIR/d-none.log"
  printf 'PLAYWRIGHT_SOURCE_PROVENANCE repo=quay/quay ref=master sha=unknown\n' >"$f_unknown"
  printf 'PLAYWRIGHT_SOURCE_PROVENANCE sha=abc123 ref=master repo=quay/quay\n' >"$f_unparseable"
  printf 'no provenance here\n' >"$f_none"

  parse_playwright_sha "$f_unknown"
  local r_unknown="$PLAYWRIGHT_SHA_REASON"
  parse_playwright_sha "$f_unparseable"
  local r_unparseable="$PLAYWRIGHT_SHA_REASON"
  parse_playwright_sha "$f_none"
  local r_none="$PLAYWRIGHT_SHA_REASON"
  parse_playwright_sha ""
  local r_absent="$PLAYWRIGHT_SHA_REASON"

  local reasons=("$r_unknown" "$r_unparseable" "$r_none" "$r_absent")
  local i j
  for ((i = 0; i < 4; i++)); do
    for ((j = i + 1; j < 4; j++)); do
      if [ "${reasons[$i]}" = "${reasons[$j]}" ]; then
        echo "  reasons not pairwise distinct: '${reasons[$i]}'" >&2
        return 1
      fi
    done
  done
}

# --- parse_clone_records / parse_finished shape guards (requirement 5) ---

# Runs func($path) inside a *freshly exec'd* bash process under set -euo
# pipefail, printing the requested globals \x1f-separated for the caller to
# inspect. This must be a new process, not a `( ... )` subshell of this
# runner: bash disables errexit for the whole dynamic extent of a command
# used as an if/while/until condition -- including any nested subshells,
# even ones with their own explicit `set -e` -- and every test here runs
# via run_test()'s `if "$1"; then`. Only a fresh exec escapes that.
run_in_guarded_subshell() {
  bash -c '
    set -euo pipefail
    . "$1"
    func="$2"
    path="$3"
    shift 3
    "$func" "$path"
    out=()
    for var in "$@"; do
      out+=("${!var}")
    done
    IFS=$'"'"'\x1f'"'"'
    printf "%s" "${out[*]}"
  ' _ "$SCRIPT_DIR/../scripts/collector-lib.sh" "$@"
}

SHAPE_REASON_CLONE="clone-records.json could not be parsed as the expected shape (array of clone records)"
SHAPE_REASON_FINISHED="finished.json could not be parsed as the expected shape (JSON object with .result)"

test_parse_clone_records_top_level_object() {
  local f="$TEST_TMP_DIR/clone-object.json" out rc=0
  printf '{"unexpected": 1}\n' >"$f"
  out=$(run_in_guarded_subshell parse_clone_records "$f" SOURCE_CLONE_SHA SOURCE_CLONE_SHA_REASON) || rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "  parse_clone_records killed the shell on a top-level JSON object (rc=$rc)" >&2
    return 1
  fi
  local sha="${out%%$'\x1f'*}" reason="${out#*$'\x1f'}"
  assert_eq "" "$sha" "top-level object leaves SHA empty" &&
    assert_eq "$SHAPE_REASON_CLONE" "$reason" "top-level object reason"
}

test_parse_clone_records_array_of_scalars() {
  local f="$TEST_TMP_DIR/clone-scalars.json" out rc=0
  printf '[1, 2, 3]\n' >"$f"
  out=$(run_in_guarded_subshell parse_clone_records "$f" SOURCE_CLONE_SHA SOURCE_CLONE_SHA_REASON) || rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "  parse_clone_records killed the shell on an array of scalars (rc=$rc)" >&2
    return 1
  fi
  local sha="${out%%$'\x1f'*}" reason="${out#*$'\x1f'}"
  assert_eq "" "$sha" "array of scalars leaves SHA empty" &&
    assert_eq "$SHAPE_REASON_CLONE" "$reason" "array of scalars reason"
}

test_parse_clone_records_non_json_bytes() {
  local f="$TEST_TMP_DIR/clone-non-json" out rc=0
  printf 'this is not json at all\n' >"$f"
  out=$(run_in_guarded_subshell parse_clone_records "$f" SOURCE_CLONE_SHA SOURCE_CLONE_SHA_REASON) || rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "  parse_clone_records killed the shell on non-JSON bytes (rc=$rc)" >&2
    return 1
  fi
  local sha="${out%%$'\x1f'*}" reason="${out#*$'\x1f'}"
  assert_eq "" "$sha" "non-JSON bytes leaves SHA empty" &&
    assert_eq "$SHAPE_REASON_CLONE" "$reason" "non-JSON bytes reason"
}

test_parse_finished_top_level_array() {
  local f="$TEST_TMP_DIR/finished-array.json" out rc=0
  printf '[1, 2, 3]\n' >"$f"
  out=$(run_in_guarded_subshell parse_finished "$f" JOB_RESULT JOB_RESULT_REASON) || rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "  parse_finished killed the shell on a top-level JSON array (rc=$rc)" >&2
    return 1
  fi
  local result="${out%%$'\x1f'*}" reason="${out#*$'\x1f'}"
  assert_eq "" "$result" "top-level array leaves JOB_RESULT empty" &&
    assert_eq "$SHAPE_REASON_FINISHED" "$reason" "top-level array reason"
}

test_parse_finished_non_json_bytes() {
  local f="$TEST_TMP_DIR/finished-non-json" out rc=0
  printf 'this is not json at all\n' >"$f"
  out=$(run_in_guarded_subshell parse_finished "$f" JOB_RESULT JOB_RESULT_REASON) || rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "  parse_finished killed the shell on non-JSON bytes (rc=$rc)" >&2
    return 1
  fi
  local result="${out%%$'\x1f'*}" reason="${out#*$'\x1f'}"
  assert_eq "" "$result" "non-JSON bytes leaves JOB_RESULT empty" &&
    assert_eq "$SHAPE_REASON_FINISHED" "$reason" "non-JSON bytes reason"
}

test_parse_clone_records_reasons_pairwise_distinct() {
  local f_shape="$TEST_TMP_DIR/d-clone-shape.json"
  local f_no_element="$TEST_TMP_DIR/d-clone-no-element.json"
  local f_no_final_sha="$TEST_TMP_DIR/d-clone-no-final-sha.json"
  local f_no_base_ref="$TEST_TMP_DIR/d-clone-no-base-ref.json"
  printf '{"unexpected": 1}\n' >"$f_shape"
  printf '[]\n' >"$f_no_element"
  printf '[{"refs": {"org": "quay", "repo": "quay", "base_ref": "master"}}]\n' >"$f_no_final_sha"
  printf '[{"refs": {"org": "quay", "repo": "quay"}, "final_sha": "abc123"}]\n' >"$f_no_base_ref"

  parse_clone_records ""
  local r_not_downloaded="$SOURCE_CLONE_SHA_REASON"
  parse_clone_records "$f_shape"
  local r_shape="$SOURCE_CLONE_SHA_REASON"
  parse_clone_records "$f_no_element"
  local r_no_element="$SOURCE_CLONE_SHA_REASON"
  parse_clone_records "$f_no_final_sha"
  local r_no_final_sha="$SOURCE_CLONE_SHA_REASON"
  parse_clone_records "$f_no_base_ref"
  local r_no_base_ref="$SOURCE_CLONE_REF_REASON"

  local reasons=("$r_not_downloaded" "$r_shape" "$r_no_element" "$r_no_final_sha" "$r_no_base_ref")
  local i j
  for ((i = 0; i < 5; i++)); do
    for ((j = i + 1; j < 5; j++)); do
      if [ "${reasons[$i]}" = "${reasons[$j]}" ]; then
        echo "  reasons not pairwise distinct: '${reasons[$i]}'" >&2
        return 1
      fi
    done
  done
}

# --- json_array / json_object_array / first_lines_json ---

test_json_array_empty() {
  assert_eq "[]" "$(json_array)" "no args produces []"
}

test_json_array_strings() {
  assert_eq '["a","b"]' "$(json_array a b | jq -c .)" "args become a JSON string array"
}

test_json_object_array_empty() {
  assert_eq "[]" "$(json_object_array)" "no args produces []"
}

test_json_object_array_objects() {
  local o1 o2
  o1=$(jq -nc '{a: 1}')
  o2=$(jq -nc '{b: 2}')
  assert_eq '[{"a":1},{"b":2}]' "$(json_object_array "$o1" "$o2" | jq -c .)" "args become a JSON object array"
}

test_first_lines_json_caps_at_40_lines() {
  local f="$TEST_TMP_DIR/many-lines.log" out
  seq 1 100 >"$f"
  out=$(first_lines_json "$f")
  assert_eq "40" "$(printf '%s' "$out" | jq 'length')" "output is capped at 40 lines"
}

test_first_lines_json_truncates_long_lines() {
  local f="$TEST_TMP_DIR/long-line.log" out
  printf '%*s\n' 600 '' | tr ' ' 'x' >"$f"
  out=$(first_lines_json "$f")
  assert_eq "500" "$(printf '%s' "$out" | jq -r '.[0] | length')" "each line is truncated to 500 chars"
}

for t in $(declare -F | awk '{print $3}' | grep '^test_'); do
  run_test "$t"
done

echo "---"
if [ "$FAIL_COUNT" -eq 0 ]; then
  echo "All tests passed."
  exit 0
else
  echo "$FAIL_COUNT test(s) failed."
  exit 1
fi
