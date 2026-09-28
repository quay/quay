#!/bin/bash
# test-jaeger-extract.sh -- runs the real jaeger-extract.sh against synthetic
# Jaeger trace chunk files, instead of mirroring its jq filter in test code.
#
# Usage:
#   bash .agents/skills/debug-playwright-prow/tests/test-jaeger-extract.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXTRACTOR="$SCRIPT_DIR/../scripts/jaeger-extract.sh"

FAIL_COUNT=0

assert_eq() {
  local expected="$1" actual="$2" msg="$3"
  if [ "$expected" != "$actual" ]; then
    echo "  assert_eq failed: $msg (expected '$expected', got '$actual')" >&2
    return 1
  fi
}

run_test() {
  if ("$1"); then
    echo "PASS: $1"
  else
    echo "FAIL: $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

# A server span matching /api/v1/repository/*/build, in a trace that also
# has a non-server sibling span (for child_operations) and an unrelated
# /healthz span (to prove endpoint matching, not "everything in the file",
# drives inclusion).
make_span() {
  local trace_id="$1" span_id="$2" kind="$3" op="$4" target="$5" status="$6" duration="$7" start_us="$8"
  jq -nc \
    --arg traceID "$trace_id" --arg spanID "$span_id" --arg op "$op" \
    --arg kind "$kind" --arg target "$target" --argjson status "$status" \
    --argjson duration "$duration" --argjson startTime "$start_us" '
    {
      traceID: $traceID, spanID: $spanID, operationName: $op, duration: $duration, startTime: $startTime,
      tags: (
        [{key: "span.kind", value: $kind}]
        + (if $target != "" then [{key: "http.target", value: $target}] else [] end)
        + (if $status != null then [{key: "http.status_code", value: $status}] else [] end)
      )
    }'
}

make_chunk() {
  # make_chunk OUT_FILE SPAN_JSON... -- groups spans into per-traceID trace
  # entries, matching Jaeger's data[].spans[] shape (child_operations is
  # scoped to spans sharing a trace, so same-traceID spans must land in the
  # same data[] entry).
  local out="$1"
  shift
  jq -sc '
    group_by(.traceID) | map({spans: .})
    | {data: .}
  ' <(printf '%s\n' "$@") >"$out"
}

run_jaeger() {
  set +e
  bash "$EXTRACTOR" "$@" >"$TMP_ROOT/stdout" 2>"$TMP_ROOT/stderr"
  JAEGER_RC=$?
  set -e
  JAEGER_STDOUT="$(cat "$TMP_ROOT/stdout")"
  JAEGER_STDERR="$(cat "$TMP_ROOT/stderr")"
}

# --- endpoint-only matches: matching span included, unrelated span excluded ---
test_endpoint_only_matches() {
  local dir="$TMP_ROOT/endpoint"
  mkdir -p "$dir"
  make_chunk "$dir/traces.json" \
    "$(make_span t1 s1 server 'POST /api/v1/repository/<name>/build' '/api/v1/repository/foo/build' 201 500 1000000000000000)" \
    "$(make_span t1 s2 client 'internal-call' '' null 10 1000000000000100)" \
    "$(make_span t2 s3 server 'GET /healthz' '/healthz' 200 5 1000000000000200)"

  run_jaeger --dir "$dir" --endpoint '/api/v1/repository/.*/build'

  assert_eq "0" "$JAEGER_RC" "exit code" &&
    assert_eq "1" "$(printf '%s' "$JAEGER_STDOUT" | jq 'length')" "only the matching endpoint span is emitted" &&
    assert_eq "s1" "$(printf '%s' "$JAEGER_STDOUT" | jq -r '.[0].span_id')" "matched span_id" &&
    assert_eq "internal-call" "$(printf '%s' "$JAEGER_STDOUT" | jq -r '.[0].child_operations[0].operation')" "child_operations from the same trace"
}

# --- time window: a since/until bound narrows candidates but never
# substitutes for the endpoint match ---
test_time_window_narrows_candidates() {
  local dir="$TMP_ROOT/timewindow"
  mkdir -p "$dir"
  make_chunk "$dir/traces.json" \
    "$(make_span t1 in-window server 'POST /api/v1/build' '/api/v1/build' 200 10 1500000000000000)" \
    "$(make_span t2 out-of-window server 'POST /api/v1/build' '/api/v1/build' 200 10 1600000000000000)"

  run_jaeger --dir "$dir" --endpoint '/api/v1/build' --since 1499999999 --until 1500000001

  assert_eq "0" "$JAEGER_RC" "exit code" &&
    assert_eq "1" "$(printf '%s' "$JAEGER_STDOUT" | jq 'length')" "only the in-window span matches" &&
    assert_eq "in-window" "$(printf '%s' "$JAEGER_STDOUT" | jq -r '.[0].span_id')" "in-window span_id"
}

# --- invalid chunk: skipped with a warning, run continues ---
test_invalid_chunk_skipped_with_warning() {
  local dir="$TMP_ROOT/invalid"
  mkdir -p "$dir"
  printf 'not valid json at all' >"$dir/traces.json"
  make_chunk "$dir/traces-2.json" \
    "$(make_span t1 s1 server 'GET /api/v1/thing' '/api/v1/thing' 200 10 1000000000000000)"

  run_jaeger --dir "$dir" --endpoint '/api/v1/thing'

  assert_eq "0" "$JAEGER_RC" "exit code (run continues past the invalid chunk)" &&
    assert_eq "1" "$(printf '%s' "$JAEGER_STDOUT" | jq 'length')" "valid chunk's match still emitted" &&
    case "$JAEGER_STDERR" in
      *"skipping invalid JSON chunk file"*) : ;;
      *)
        echo "  expected a skip warning for the invalid chunk, got: $JAEGER_STDERR" >&2
        return 1
        ;;
    esac
}

# --- max-files: only the first N chunk files (by name) are read ---
test_max_files_caps_chunks_read() {
  local dir="$TMP_ROOT/maxfiles"
  mkdir -p "$dir"
  make_chunk "$dir/traces.json" \
    "$(make_span t1 s1 server 'GET /api/v1/x' '/api/v1/x' 200 10 1000000000000000)"
  make_chunk "$dir/traces-1.json" \
    "$(make_span t2 s2 server 'GET /api/v1/x' '/api/v1/x' 200 10 1000000000000000)"
  make_chunk "$dir/traces-2.json" \
    "$(make_span t3 s3 server 'GET /api/v1/x' '/api/v1/x' 200 10 1000000000000000)"

  run_jaeger --dir "$dir" --endpoint '/api/v1/x' --max-files 1

  assert_eq "0" "$JAEGER_RC" "exit code" &&
    assert_eq "1" "$(printf '%s' "$JAEGER_STDOUT" | jq 'length')" "only the first chunk file is read" &&
    assert_eq "s1" "$(printf '%s' "$JAEGER_STDOUT" | jq -r '.[0].span_id')" "match came from traces.json, not the later chunks" &&
    case "$JAEGER_STDERR" in
      *"--max-files"*) : ;;
      *)
        echo "  expected a --max-files warning, got: $JAEGER_STDERR" >&2
        return 1
        ;;
    esac
}

# --- max-records: once the cap is reached, remaining chunk files are
# skipped (with a warning) rather than read for no purpose ---
test_max_records_truncates_matches() {
  local dir="$TMP_ROOT/maxrecords"
  mkdir -p "$dir"
  make_chunk "$dir/traces.json" \
    "$(make_span t1 s1 server 'GET /api/v1/y' '/api/v1/y' 200 10 1000000000000000)" \
    "$(make_span t2 s2 server 'GET /api/v1/y' '/api/v1/y' 200 10 1000000000000001)"
  make_chunk "$dir/traces-1.json" \
    "$(make_span t3 s3 server 'GET /api/v1/y' '/api/v1/y' 200 10 1000000000000002)"

  run_jaeger --dir "$dir" --endpoint '/api/v1/y' --max-records 2

  assert_eq "0" "$JAEGER_RC" "exit code" &&
    assert_eq "2" "$(printf '%s' "$JAEGER_STDOUT" | jq 'length')" "output capped at --max-records" &&
    case "$JAEGER_STDERR" in
      *"--max-records"*) : ;;
      *)
        echo "  expected a --max-records warning, got: $JAEGER_STDERR" >&2
        return 1
        ;;
    esac
}

# --- max-records: the cap can also be hit inside the last (or only) chunk
# file, where there is no following file to trigger the top-of-loop warning
# -- a capped result must still be distinguishable from a complete one ---
test_max_records_hit_in_last_chunk_still_warns() {
  local dir="$TMP_ROOT/maxrecordslast"
  mkdir -p "$dir"
  make_chunk "$dir/traces.json" \
    "$(make_span t1 s1 server 'GET /api/v1/z' '/api/v1/z' 200 10 1000000000000000)" \
    "$(make_span t2 s2 server 'GET /api/v1/z' '/api/v1/z' 200 10 1000000000000001)" \
    "$(make_span t3 s3 server 'GET /api/v1/z' '/api/v1/z' 200 10 1000000000000002)"

  run_jaeger --dir "$dir" --endpoint '/api/v1/z' --max-records 2

  assert_eq "0" "$JAEGER_RC" "exit code" &&
    assert_eq "2" "$(printf '%s' "$JAEGER_STDOUT" | jq 'length')" "output capped at --max-records" &&
    case "$JAEGER_STDERR" in
      *"--max-records"*) : ;;
      *)
        echo "  expected a --max-records warning even with no following chunk file, got: $JAEGER_STDERR" >&2
        return 1
        ;;
    esac
}

# --- max-records: a chunk with exactly --max-records matches is complete,
# not capped -- nothing was dropped, so no "output capped" warning ---
test_max_records_exact_limit_no_false_positive() {
  local dir="$TMP_ROOT/maxrecordsexact"
  mkdir -p "$dir"
  make_chunk "$dir/traces.json" \
    "$(make_span t1 s1 server 'GET /api/v1/y' '/api/v1/y' 200 10 1000000000000000)" \
    "$(make_span t2 s2 server 'GET /api/v1/y' '/api/v1/y' 200 10 1000000000000001)"

  run_jaeger --dir "$dir" --endpoint '/api/v1/y' --max-records 2

  assert_eq "0" "$JAEGER_RC" "exit code" &&
    assert_eq "2" "$(printf '%s' "$JAEGER_STDOUT" | jq 'length')" "all matches returned" &&
    case "$JAEGER_STDERR" in
      *"capped"*)
        echo "  expected no capped warning for a complete result, got: $JAEGER_STDERR" >&2
        return 1
        ;;
      *) : ;;
    esac
}

# --- a matching span preceding a span that makes jq error mid-file must not
# leave a partial record in the output; the whole file is skipped, not
# half-written ---
test_partial_records_not_written_on_mid_file_error() {
  local dir="$TMP_ROOT/partialerror"
  mkdir -p "$dir"
  jq -n '
    {
      data: [
        {
          spans: [
            {
              traceID: "t1", spanID: "s1", operationName: "GET /api/v1/ok", duration: 10, startTime: 1000000000000000,
              tags: [{key: "span.kind", value: "server"}, {key: "http.target", value: "/api/v1/ok"}]
            }
          ]
        },
        {
          spans: [
            {
              traceID: "t2", spanID: "s2", operationName: "GET /api/v1/bad", duration: 10, startTime: 1000000000000001,
              tags: [{key: "span.kind", value: "server"}, {key: "http.target", value: 12345}]
            }
          ]
        }
      ]
    }
  ' >"$dir/traces.json"

  run_jaeger --dir "$dir" --endpoint '/api/v1/'

  assert_eq "0" "$JAEGER_RC" "exit code (a per-file jq error is a warning, not a failure)" &&
    assert_eq "0" "$(printf '%s' "$JAEGER_STDOUT" | jq 'length')" "no records from a file with a mid-file jq error" &&
    case "$JAEGER_STDERR" in
      *"jq failed while scanning"*) : ;;
      *)
        echo "  expected a jq-failed warning, got: $JAEGER_STDERR" >&2
        return 1
        ;;
    esac
}

# --- invalid --endpoint regex: rejected up front, not read as "no spans" ---
test_invalid_endpoint_regex_rejected() {
  local dir="$TMP_ROOT/badregex"
  mkdir -p "$dir"
  make_chunk "$dir/traces.json" \
    "$(make_span t1 s1 server 'GET /api/v1/x' '/api/v1/x' 200 10 1000000000000000)"

  run_jaeger --dir "$dir" --endpoint '/api/v1/x('

  assert_eq "1" "$JAEGER_RC" "exit code (invalid regex is a usage error)" &&
    case "$JAEGER_STDERR" in
      *"not a valid regular expression"*) : ;;
      *)
        echo "  expected an invalid-regex error, got: $JAEGER_STDERR" >&2
        return 1
        ;;
    esac
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
