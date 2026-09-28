#!/bin/bash
# test-collector-fixtures.sh -- integration tests that run the real
# playwright-debug-prow.sh against a synthetic GCS bucket, instead of
# mirroring its jq/case logic in test code. Stubs curl with a fake GCS
# object/listing server backed by files under a disposable fixture
# directory (removed on exit); jq is the real binary.
#
# Usage:
#   bash .agents/skills/debug-playwright-prow/tests/test-collector-fixtures.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COLLECTOR="$SCRIPT_DIR/../scripts/playwright-debug-prow.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR" && git rev-parse --show-toplevel)"

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

BUCKET="test-bucket"
JOB_PATH="logs/pull-ci-quay-quay-master-e2e/1000"
BUILD_ID="42"
PROW_URL="https://prow.ci.openshift.org/view/gs/${BUCKET}/${JOB_PATH}/${BUILD_ID}"
GCS_BASE_REL="${JOB_PATH}/${BUILD_ID}"

REDACTION_PLACEHOLDER='This file contained potentially sensitive information and has been removed.'

# --- Mock curl: a fake GCS object/listing server backed by files under
# MOCK_GCS_ROOT, keyed by MOCK_GCS_BUCKET. Written once; each test exports
# fresh MOCK_GCS_ROOT/MOCK_GCS_BUCKET values before invoking the collector.
BINDIR="$TMP_ROOT/bin"
mkdir -p "$BINDIR"
cat >"$BINDIR/curl" <<'MOCKCURL'
#!/bin/bash
set -euo pipefail
BUCKET_URL="https://storage.googleapis.com/${MOCK_GCS_BUCKET}"

is_head=false
out_file=""
range=""
have_w=false
url=""
declare -a data_params=()

args=("$@")
n="${#args[@]}"
i=0
while [ "$i" -lt "$n" ]; do
  a="${args[$i]}"
  case "$a" in
    --head) is_head=true ;;
    -o)
      i=$((i + 1))
      out_file="${args[$i]}"
      ;;
    -r)
      i=$((i + 1))
      range="${args[$i]}"
      ;;
    -w)
      i=$((i + 1))
      have_w=true
      ;;
    --data-urlencode)
      i=$((i + 1))
      data_params+=("${args[$i]}")
      ;;
    --connect-timeout | --max-time | --max-filesize)
      i=$((i + 1))
      ;;
    --get) : ;;
    -*) : ;;
    *) url="$a" ;;
  esac
  i=$((i + 1))
done

declare -A params=()
for kv in "${data_params[@]}"; do
  params["${kv%%=*}"]="${kv#*=}"
done
if [[ "$url" == *'?'* ]]; then
  qs="${url#*\?}"
  IFS='&' read -ra pairs <<<"$qs"
  for kv in "${pairs[@]}"; do
    params["${kv%%=*}"]="${kv#*=}"
  done
  url="${url%%\?*}"
fi

# --- Listing: bucket-root URL, either delimiter (common-prefix) or full
# recursive prefix listing, backed by the fixture directory tree.
if [ "$url" = "$BUCKET_URL" ]; then
  prefix="${params[prefix]:-}"
  delimiter="${params[delimiter]:-}"
  target_dir="$MOCK_GCS_ROOT/$prefix"
  echo '<?xml version="1.0"?><ListBucketResult>'
  if [ "$delimiter" = "/" ]; then
    if [ -d "$target_dir" ]; then
      find "$target_dir" -mindepth 1 -maxdepth 1 -type d | sort | while IFS= read -r d; do
        echo "<Prefix>${prefix}$(basename "$d")/</Prefix>"
      done
    fi
  else
    if [ -d "$target_dir" ]; then
      find "$target_dir" -type f ! -name '*.http_code' | sort | while IFS= read -r f; do
        echo "<Key>${f#"$MOCK_GCS_ROOT"/}</Key>"
      done
    fi
  fi
  echo '</ListBucketResult>'
  exit 0
fi

# --- Object HEAD/GET, backed by a single fixture file. A sibling
# "$file.http_code" overrides the HEAD status (e.g. "403", "500") so a
# fixture can force classify_object_head's head_failed path without the
# object actually being 404.
rel_path="${url#"$BUCKET_URL"/}"
file="$MOCK_GCS_ROOT/$rel_path"

if [ "$is_head" = "true" ]; then
  if [ -f "${file}.http_code" ]; then
    code="$(cat "${file}.http_code")"
  elif [ -f "$file" ]; then
    code=200
  else
    code=404
  fi
  [ -n "$out_file" ] && : >"$out_file"
  if [ "$have_w" = "true" ]; then
    printf '%s' "$code"
    exit 0
  fi
  [ "$code" = "200" ] && exit 0
  exit 22
fi

if [ ! -f "$file" ]; then
  exit 22
fi

if [ -n "$range" ]; then
  start="${range%-*}"
  end="${range#*-}"
  len=$((end - start + 1))
  if [ -n "$out_file" ]; then
    dd if="$file" of="$out_file" bs=1 skip="$start" count="$len" 2>/dev/null
  else
    dd if="$file" bs=1 skip="$start" count="$len" 2>/dev/null
  fi
elif [ -n "$out_file" ]; then
  cp "$file" "$out_file"
else
  cat "$file"
fi
exit 0
MOCKCURL
chmod +x "$BINDIR/curl"

# Runs the real collector against $1 (a fixture root dir mirroring the GCS
# bucket), setting COLLECTOR_RC/COLLECTOR_STDOUT/COLLECTOR_STDERR.
run_collector() {
  local root="$1"
  set +e
  MOCK_GCS_BUCKET="$BUCKET" MOCK_GCS_ROOT="$root" PATH="$BINDIR:$PATH" \
    bash "$COLLECTOR" "$PROW_URL" >"$TMP_ROOT/stdout" 2>"$TMP_ROOT/stderr"
  COLLECTOR_RC=$?
  set -e
  COLLECTOR_STDOUT="$(cat "$TMP_ROOT/stdout")"
  COLLECTOR_STDERR="$(cat "$TMP_ROOT/stderr")"
}

new_fixture_root() { mktemp -d "$TMP_ROOT/fixture.XXXXXX"; }

write_prowjob() {
  local root="$1" body="${2:-}"
  [ -n "$body" ] || body='{"status":{"state":"success"}}'
  mkdir -p "$root/$GCS_BASE_REL"
  printf '%s' "$body" >"$root/$GCS_BASE_REL/prowjob.json"
}

# --- T1: direct nested layout, gather-extra/Jaeger siblings, kept on success ---
test_nested_layout_direct_step_and_siblings() {
  local root artifacts_dir
  root="$(new_fixture_root)"
  trap '[ -n "${artifacts_dir:-}" ] && rm -rf "$artifacts_dir"' RETURN
  write_prowjob "$root"

  local step_dir="$root/$GCS_BASE_REL/artifacts/quay-test-e2e/artifacts"
  mkdir -p "$step_dir"
  cat >"$step_dir/results.json" <<'EOF'
{"config":{"workers":2},"suites":[{"specs":[]}],"stats":{"expected":1,"unexpected":0,"flaky":0,"skipped":0,"duration":100,"startTime":"2026-01-01T00:00:00.000Z"},"errors":[]}
EOF

  local extra_dir="$root/$GCS_BASE_REL/artifacts/gather-extra/artifacts/pods"
  mkdir -p "$extra_dir"
  printf 'quay app log line\n' >"$extra_dir/quay-app-1_quay-app.log"

  local jaeger_dir="$root/$GCS_BASE_REL/artifacts/quay-gather-jaeger-traces/artifacts/jaeger-traces"
  mkdir -p "$jaeger_dir"
  printf '{"data":[]}' >"$jaeger_dir/traces.json"

  run_collector "$root"
  artifacts_dir="$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifacts_dir')"

  assert_eq "0" "$COLLECTOR_RC" "exit code" &&
    assert_eq "https://storage.googleapis.com/${BUCKET}/${GCS_BASE_REL}/artifacts/quay-test-e2e/artifacts" \
      "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifact_base_url')" "artifact_base_url (nested)" &&
    assert_eq "true" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.has_container_logs')" "has_container_logs" &&
    assert_eq "quay-app-1_quay-app.log" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.container_log_files[0]')" "container_log_files" &&
    assert_eq "true" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.has_jaeger_traces')" "has_jaeger_traces" &&
    assert_eq "traces.json" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.jaeger_trace_files[0]')" "jaeger_trace_files" &&
    assert_eq "${REPO_ROOT}/tmp" "$(dirname "$artifacts_dir")" "artifacts_dir lives under repo tmp/" &&
    [ -d "$artifacts_dir" ]
}

# --- T2: flat layout (no nested "/artifacts" under the step) ---
test_flat_layout_step_and_siblings() {
  local root artifacts_dir
  root="$(new_fixture_root)"
  trap '[ -n "${artifacts_dir:-}" ] && rm -rf "$artifacts_dir"' RETURN
  write_prowjob "$root"

  local step_dir="$root/$GCS_BASE_REL/artifacts/quay-test-e2e"
  mkdir -p "$step_dir"
  cat >"$step_dir/results.json" <<'EOF'
{"config":{"workers":2},"suites":[{"specs":[]}],"stats":{"expected":1,"unexpected":0,"flaky":0,"skipped":0,"duration":100,"startTime":"2026-01-01T00:00:00.000Z"},"errors":[]}
EOF
  printf 'step build log\n' >"$step_dir/build-log.txt"

  local extra_dir="$root/$GCS_BASE_REL/artifacts/gather-extra/artifacts/pods"
  mkdir -p "$extra_dir"
  printf 'quay app log line\n' >"$extra_dir/quay-app-1_quay-app.log"

  run_collector "$root"
  artifacts_dir="$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifacts_dir')"

  assert_eq "0" "$COLLECTOR_RC" "exit code" &&
    assert_eq "https://storage.googleapis.com/${BUCKET}/${GCS_BASE_REL}/artifacts/quay-test-e2e" \
      "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifact_base_url')" "artifact_base_url (flat)" &&
    assert_eq "true" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.has_build_log')" "has_build_log (flat step-local log)" &&
    assert_eq "true" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.has_container_logs')" "has_container_logs (flat siblings still resolve)"
}

# --- T3: nested workflow/step discovery, surviving a non-matching candidate ---
test_nested_workflow_discovery_survives_unrelated() {
  local root artifacts_dir
  root="$(new_fixture_root)"
  trap '[ -n "${artifacts_dir:-}" ] && rm -rf "$artifacts_dir"' RETURN
  write_prowjob "$root"

  # A workflow dir with a step that has no results.json anywhere (sorts
  # before "e2e" so it is probed first).
  mkdir -p "$root/$GCS_BASE_REL/artifacts/aaa-other-workflow/setup-step/artifacts"

  # The real workflow: results.json nested one level deeper than the
  # workflow dir (artifacts/e2e/quay-test-playwright/artifacts/results.json).
  local step_dir="$root/$GCS_BASE_REL/artifacts/e2e/quay-test-playwright/artifacts"
  mkdir -p "$step_dir"
  cat >"$step_dir/results.json" <<'EOF'
{"config":{"workers":1},"suites":[{"specs":[]}],"stats":{"expected":1,"unexpected":0,"flaky":0,"skipped":0,"duration":100,"startTime":"2026-01-01T00:00:00.000Z"},"errors":[]}
EOF

  run_collector "$root"
  artifacts_dir="$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifacts_dir')"

  assert_eq "0" "$COLLECTOR_RC" "exit code" &&
    assert_eq "https://storage.googleapis.com/${BUCKET}/${GCS_BASE_REL}/artifacts/e2e/quay-test-playwright/artifacts" \
      "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifact_base_url')" "discovers nested quay-test-playwright step"
}

# --- T4: actual_workers project value / root fallback / both missing ---
test_actual_workers_fallback_three_cases() {
  local root artifacts_dir
  root="$(new_fixture_root)"
  trap '[ -n "${artifacts_dir:-}" ] && rm -rf "$artifacts_dir"' RETURN
  write_prowjob "$root"
  local step_dir="$root/$GCS_BASE_REL/artifacts/quay-test-e2e/artifacts"
  mkdir -p "$step_dir"

  local stats='"stats":{"expected":1,"unexpected":0,"flaky":0,"skipped":0,"duration":100,"startTime":"2026-01-01T00:00:00.000Z"},"errors":[]'

  # (a) per-project metadata.actualWorkers present.
  printf '{"config":{"workers":8,"projects":[{"metadata":{"actualWorkers":4}}]},"suites":[{"specs":[]}],%s}' "$stats" >"$step_dir/results.json"
  run_collector "$root"
  artifacts_dir="$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifacts_dir')"
  assert_eq "0" "$COLLECTOR_RC" "exit code (project value)" &&
    assert_eq "4" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.provenance.actual_workers.value')" "actual_workers uses project value" &&
    assert_eq "null" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.provenance.actual_workers.reason')" "reason null for project value" || return 1
  rm -rf "$artifacts_dir"

  # (b) no per-project metadata, root config.workers present -> fallback.
  printf '{"config":{"workers":8,"projects":[{}]},"suites":[{"specs":[]}],%s}' "$stats" >"$step_dir/results.json"
  run_collector "$root"
  artifacts_dir="$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifacts_dir')"
  assert_eq "0" "$COLLECTOR_RC" "exit code (root fallback)" &&
    assert_eq "8" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.provenance.actual_workers.value')" "actual_workers falls back to root config.workers" &&
    assert_eq "config.projects[].metadata.actualWorkers not present in results.json; using root config.workers" \
      "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.provenance.actual_workers.reason')" "reason names the root fallback" || return 1
  rm -rf "$artifacts_dir"

  # (c) both missing -> null with a reason naming both fields.
  printf '{"config":{"projects":[{}]},"suites":[{"specs":[]}],%s}' "$stats" >"$step_dir/results.json"
  run_collector "$root"
  artifacts_dir="$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifacts_dir')"
  assert_eq "0" "$COLLECTOR_RC" "exit code (both missing)" &&
    assert_eq "null" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.provenance.actual_workers.value')" "actual_workers null when both sources missing" &&
    assert_eq "config.projects[].metadata.actualWorkers and root config.workers not present in results.json" \
      "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.provenance.actual_workers.reason')" "reason names both fields missing"
}

# --- T5: attachment validation -- usable trace, missing, and redacted ---
test_attachment_validation_usable_missing_redacted() {
  local root artifacts_dir
  root="$(new_fixture_root)"
  trap '[ -n "${artifacts_dir:-}" ] && rm -rf "$artifacts_dir"' RETURN
  write_prowjob "$root"

  local step_dir="$root/$GCS_BASE_REL/artifacts/quay-test-e2e/artifacts"
  mkdir -p "$step_dir/attach-coverage"
  cat >"$step_dir/results.json" <<'EOF'
{"config":{"workers":1},"suites":[{"specs":[{"title":"attachment coverage","file":"attach.spec.ts","line":5,"tests":[{"projectName":"chromium","status":"unexpected","results":[{"retry":0,"status":"failed","duration":50,"errors":[{"message":"failure"}],"attachments":[{"name":"trace","path":"/work/test-results/attach-coverage/trace.zip"},{"name":"screenshot","path":"/work/test-results/attach-coverage/missing.png"},{"name":"screenshot","path":"/work/test-results/attach-coverage/redacted.png"},{"name":"trace","path":"/work/test-results/attach-coverage/badmagic-trace.zip"},{"name":"trace","path":"/work/test-results/attach-coverage/corrupt-trace.zip"}]}]}]}]}],"stats":{"expected":0,"unexpected":1,"flaky":0,"skipped":0,"duration":50,"startTime":"2026-01-01T00:00:00.000Z"},"errors":[]}
EOF

  TRACE_ZIP_PATH="$step_dir/attach-coverage/trace.zip" python3 - <<'PY'
import os, zipfile
zipfile.ZipFile(os.environ["TRACE_ZIP_PATH"], "w").writestr("trace.trace", b"hello")
PY
  # missing.png is intentionally never created (download failure).
  printf '%s' "$REDACTION_PLACEHOLDER" >"$step_dir/attach-coverage/redacted.png"
  # Not a zip at all -- no "PK" magic bytes.
  printf 'not a zip file' >"$step_dir/attach-coverage/badmagic-trace.zip"
  # Starts with the "PK" magic bytes but the archive body is garbage, so
  # `unzip -tq` fails the integrity check.
  printf 'PK\x03\x04garbage, not a real central directory' >"$step_dir/attach-coverage/corrupt-trace.zip"

  run_collector "$root"
  artifacts_dir="$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifacts_dir')"

  local attachments
  attachments="$(printf '%s' "$COLLECTOR_STDOUT" | jq -c '.failed[0].attempts[0].attachments')"

  assert_eq "0" "$COLLECTOR_RC" "exit code" &&
    assert_eq "usable" "$(printf '%s' "$attachments" | jq -r '.[0].status')" "valid trace zip is usable" &&
    assert_eq "missing" "$(printf '%s' "$attachments" | jq -r '.[1].status')" "undownloadable attachment is missing" &&
    assert_eq "download failed" "$(printf '%s' "$attachments" | jq -r '.[1].reason')" "missing attachment reason" &&
    assert_eq "redacted" "$(printf '%s' "$attachments" | jq -r '.[2].status')" "CI-redacted attachment is redacted" &&
    assert_eq "CI sensitive-content placeholder" "$(printf '%s' "$attachments" | jq -r '.[2].reason')" "redacted attachment reason" &&
    assert_eq "missing" "$(printf '%s' "$attachments" | jq -r '.[3].status')" "non-zip trace is missing" &&
    assert_eq "not a valid zip (bad magic bytes)" "$(printf '%s' "$attachments" | jq -r '.[3].reason')" "bad magic bytes reason" &&
    assert_eq "missing" "$(printf '%s' "$attachments" | jq -r '.[4].status')" "corrupt zip trace is missing" &&
    assert_eq "unzip -t failed (corrupt archive)" "$(printf '%s' "$attachments" | jq -r '.[4].reason')" "corrupt archive reason" &&
    assert_eq "traces captured on failing/retried attempts (inferred from 3 trace attachment(s) in results.json; config.projects[].use.trace not serialized)" \
      "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.provenance.tracing_configuration.value')" "tracing_configuration inferred from trace attachments" &&
    assert_eq "null" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.provenance.tracing_configuration.reason')" "tracing_configuration reason null when inferred"
}

# --- T6: must-gather evidence gaps -- redacted, and absent (not a gap) ---
test_must_gather_evidence_gaps() {
  local root artifacts_dir
  root="$(new_fixture_root)"
  trap '[ -n "${artifacts_dir:-}" ] && rm -rf "$artifacts_dir"' RETURN
  write_prowjob "$root"
  local step_dir="$root/$GCS_BASE_REL/artifacts/quay-test-e2e/artifacts"
  mkdir -p "$step_dir"
  cat >"$step_dir/results.json" <<'EOF'
{"config":{"workers":1},"suites":[{"specs":[]}],"stats":{"expected":1,"unexpected":0,"flaky":0,"skipped":0,"duration":100,"startTime":"2026-01-01T00:00:00.000Z"},"errors":[]}
EOF

  # (a) must-gather.tar exists but is the CI redaction placeholder.
  local mg_dir="$root/$GCS_BASE_REL/artifacts/gather-must-gather/artifacts"
  mkdir -p "$mg_dir"
  printf '%s' "$REDACTION_PLACEHOLDER" >"$mg_dir/must-gather.tar"

  run_collector "$root"
  artifacts_dir="$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifacts_dir')"
  assert_eq "0" "$COLLECTOR_RC" "exit code (redacted must-gather)" &&
    assert_eq "1" "$(printf '%s' "$COLLECTOR_STDOUT" | jq '.evidence_gaps | length')" "one evidence gap recorded" &&
    assert_eq "redacted" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.evidence_gaps[0].status')" "must-gather gap status" || return 1
  rm -rf "$artifacts_dir"

  # (b) must-gather.tar was never produced (step didn't run) -> no gap.
  rm -rf "$root/$GCS_BASE_REL/artifacts/gather-must-gather"
  run_collector "$root"
  artifacts_dir="$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifacts_dir')"
  assert_eq "0" "$COLLECTOR_RC" "exit code (absent must-gather)" &&
    assert_eq "0" "$(printf '%s' "$COLLECTOR_STDOUT" | jq '.evidence_gaps | length')" "absent must-gather step is not reported as a gap"
}

# --- T7: routing records and provenance ---
test_routing_records_and_provenance() {
  local root artifacts_dir
  root="$(new_fixture_root)"
  trap '[ -n "${artifacts_dir:-}" ] && rm -rf "$artifacts_dir"' RETURN
  write_prowjob "$root" '{"status":{"state":"success"},"spec":{"extra_refs":[{"org":"openshift","repo":"release","base_sha":"relconfsha123"}]}}'

  printf '[{"refs":{}},{"refs":{"org":"quay","repo":"quay","base_ref":"master"},"final_sha":"clonesha456"}]' \
    >"$root/$GCS_BASE_REL/clone-records.json"
  printf '{"result":"FAILURE","revision":"finishedrevision789"}' >"$root/$GCS_BASE_REL/finished.json"
  printf 'Image quay-playwright-runner created digest=sha256:cafebabe1234\n' >"$root/$GCS_BASE_REL/build-log.txt"

  local step_dir="$root/$GCS_BASE_REL/artifacts/quay-test-e2e/artifacts"
  mkdir -p "$step_dir"
  cat >"$step_dir/results.json" <<'EOF'
{"config":{"workers":1},"suites":[{"specs":[]}],"stats":{"expected":1,"unexpected":0,"flaky":0,"skipped":0,"duration":100,"startTime":"2026-01-01T00:00:00.000Z"},"errors":[]}
EOF
  printf 'PLAYWRIGHT_SOURCE_PROVENANCE repo=quay/quay ref=master sha=abc123def\n' \
    >"$root/$GCS_BASE_REL/artifacts/quay-test-e2e/build-log.txt"
  printf '<testsuite/>' >"$step_dir/junit_playwright.xml"

  run_collector "$root"
  artifacts_dir="$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifacts_dir')"
  local prov
  prov="$(printf '%s' "$COLLECTOR_STDOUT" | jq -c '.provenance')"

  assert_eq "0" "$COLLECTOR_RC" "exit code" &&
    assert_eq "downloaded" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.prowjob.status')" "prowjob routing record" &&
    assert_eq "downloaded" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.clone_records.status')" "clone_records routing record" &&
    assert_eq "downloaded" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.finished.status')" "finished routing record" &&
    assert_eq "downloaded" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.junit[0].status')" "junit routing record" &&
    assert_eq "clonesha456" "$(printf '%s' "$prov" | jq -r '.source_clone_sha.value')" "source_clone_sha" &&
    assert_eq "master" "$(printf '%s' "$prov" | jq -r '.source_clone_ref.value')" "source_clone_ref" &&
    assert_eq "FAILURE" "$(printf '%s' "$prov" | jq -r '.job_result.value')" "job_result" &&
    assert_eq "abc123def" "$(printf '%s' "$prov" | jq -r '.playwright_sha.value')" "playwright_sha" &&
    assert_eq "sha256:cafebabe1234" "$(printf '%s' "$prov" | jq -r '.source_image_digest.value')" "source_image_digest" &&
    assert_eq "relconfsha123" "$(printf '%s' "$prov" | jq -r '.release_config_revision.value')" "release_config_revision"
}

# --- T8: artifacts_dir is removed on a failed run ---
test_removed_on_failed_run() {
  local root work_dir
  root="$(new_fixture_root)"
  write_prowjob "$root"
  # No results.json anywhere under artifacts/ -- discovery must fail.

  run_collector "$root"
  work_dir="$(printf '%s' "$COLLECTOR_STDERR" | sed -n 's/^Downloading artifacts to \(.*\) \.\.\.$/\1/p' | head -1)"

  assert_eq "1" "$COLLECTOR_RC" "exit code (no results.json found)" &&
    [ -n "$work_dir" ] &&
    [ ! -d "$work_dir" ]
}

# --- source_clone_ref falls back to finished.json's .revision when
# clone-records.json has a matching element with no refs.base_ref ---
test_source_clone_ref_falls_back_to_finished_revision() {
  local root artifacts_dir
  root="$(new_fixture_root)"
  trap '[ -n "${artifacts_dir:-}" ] && rm -rf "$artifacts_dir"' RETURN
  write_prowjob "$root"

  printf '[{"refs":{"org":"quay","repo":"quay"}}]' >"$root/$GCS_BASE_REL/clone-records.json"
  printf '{"result":"SUCCESS","revision":"revfallback999"}' >"$root/$GCS_BASE_REL/finished.json"

  local step_dir="$root/$GCS_BASE_REL/artifacts/quay-test-e2e/artifacts"
  mkdir -p "$step_dir"
  cat >"$step_dir/results.json" <<'EOF'
{"config":{"workers":1},"suites":[{"specs":[]}],"stats":{"expected":1,"unexpected":0,"flaky":0,"skipped":0,"duration":100,"startTime":"2026-01-01T00:00:00.000Z"},"errors":[]}
EOF

  run_collector "$root"
  artifacts_dir="$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifacts_dir')"

  assert_eq "0" "$COLLECTOR_RC" "exit code" &&
    assert_eq "revfallback999" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.provenance.source_clone_ref.value')" \
      "source_clone_ref falls back to finished.json revision" &&
    assert_eq "null" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.provenance.source_clone_ref.reason')" \
      "source_clone_ref reason null when the fallback resolves it"
}

# --- index.html itself is the CI redaction placeholder ---
test_html_report_redacted() {
  local root artifacts_dir
  root="$(new_fixture_root)"
  trap '[ -n "${artifacts_dir:-}" ] && rm -rf "$artifacts_dir"' RETURN
  write_prowjob "$root"

  local step_dir="$root/$GCS_BASE_REL/artifacts/quay-test-e2e/artifacts"
  mkdir -p "$step_dir"
  cat >"$step_dir/results.json" <<'EOF'
{"config":{"workers":1},"suites":[{"specs":[]}],"stats":{"expected":1,"unexpected":0,"flaky":0,"skipped":0,"duration":100,"startTime":"2026-01-01T00:00:00.000Z"},"errors":[]}
EOF
  printf '%s' "$REDACTION_PLACEHOLDER" >"$step_dir/index.html"

  run_collector "$root"
  artifacts_dir="$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifacts_dir')"

  assert_eq "0" "$COLLECTOR_RC" "exit code" &&
    assert_eq "" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.html_report_url')" \
      "html_report_url empty when index.html is the redaction placeholder"
}

# --- an HTML-report data/ blob comes back redacted ---
test_html_report_data_blob_redacted() {
  local root artifacts_dir
  root="$(new_fixture_root)"
  trap '[ -n "${artifacts_dir:-}" ] && rm -rf "$artifacts_dir"' RETURN
  write_prowjob "$root"

  local step_dir="$root/$GCS_BASE_REL/artifacts/quay-test-e2e/artifacts"
  mkdir -p "$step_dir/data"
  cat >"$step_dir/results.json" <<'EOF'
{"config":{"workers":1},"suites":[{"specs":[]}],"stats":{"expected":1,"unexpected":0,"flaky":0,"skipped":0,"duration":100,"startTime":"2026-01-01T00:00:00.000Z"},"errors":[]}
EOF
  printf '%s' "$REDACTION_PLACEHOLDER" >"$step_dir/data/redacted-blob.zip"

  run_collector "$root"
  artifacts_dir="$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifacts_dir')"

  assert_eq "0" "$COLLECTOR_RC" "exit code" &&
    assert_eq "1" "$(printf '%s' "$COLLECTOR_STDOUT" | jq '.evidence_gaps | length')" "one evidence gap recorded" &&
    assert_eq "data/redacted-blob.zip" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.evidence_gaps[0].artifact')" "data/ blob gap is prefixed data/" &&
    assert_eq "redacted" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.evidence_gaps[0].status')" "data/ blob gap status"
}

# --- an HTML-report data/ blob's HEAD probe itself fails (403/500), not a
# plain 404 -- must still surface as an evidence gap, not silently drop ---
test_html_report_data_blob_head_failed() {
  local root artifacts_dir
  root="$(new_fixture_root)"
  trap '[ -n "${artifacts_dir:-}" ] && rm -rf "$artifacts_dir"' RETURN
  write_prowjob "$root"

  local step_dir="$root/$GCS_BASE_REL/artifacts/quay-test-e2e/artifacts"
  mkdir -p "$step_dir/data"
  cat >"$step_dir/results.json" <<'EOF'
{"config":{"workers":1},"suites":[{"specs":[]}],"stats":{"expected":1,"unexpected":0,"flaky":0,"skipped":0,"duration":100,"startTime":"2026-01-01T00:00:00.000Z"},"errors":[]}
EOF
  printf 'x' >"$step_dir/data/forbidden-blob.zip"
  printf '403' >"$step_dir/data/forbidden-blob.zip.http_code"

  run_collector "$root"
  artifacts_dir="$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifacts_dir')"

  assert_eq "0" "$COLLECTOR_RC" "exit code" &&
    assert_eq "1" "$(printf '%s' "$COLLECTOR_STDOUT" | jq '.evidence_gaps | length')" "one evidence gap recorded" &&
    assert_eq "data/forbidden-blob.zip" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.evidence_gaps[0].artifact')" "data/ blob gap is prefixed data/" &&
    assert_eq "missing" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.evidence_gaps[0].status')" "data/ blob gap status" &&
    assert_eq "HEAD probe failed" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.evidence_gaps[0].reason')" "data/ blob gap reason"
}

# --- attachment checks stop at MAX_DISCOVERED_ARTIFACTS, the excess is
# reported missing/capped rather than downloaded ---
test_attachment_cap_exceeded() {
  local root artifacts_dir step_dir
  root="$(new_fixture_root)"
  trap '[ -n "${artifacts_dir:-}" ] && rm -rf "$artifacts_dir"' RETURN
  write_prowjob "$root"

  step_dir="$root/$GCS_BASE_REL/artifacts/quay-test-e2e/artifacts"
  mkdir -p "$step_dir/attach-cap"

  python3 - "$step_dir" <<'PY'
import json
import os
import sys

step_dir = sys.argv[1]
attachments = []
for i in range(1, 102):
    name = f"screenshot-{i:03d}.png"
    attachments.append({"name": "screenshot", "path": f"/work/test-results/attach-cap/{name}"})
    with open(os.path.join(step_dir, "attach-cap", name), "w") as f:
        f.write("x")

results = {
    "config": {"workers": 1},
    "suites": [{
        "specs": [{
            "title": "attachment cap", "file": "cap.spec.ts", "line": 1,
            "tests": [{
                "projectName": "chromium", "status": "unexpected",
                "results": [{
                    "retry": 0, "status": "failed", "duration": 10,
                    "errors": [{"message": "failure"}],
                    "attachments": attachments,
                }],
            }],
        }],
    }],
    "stats": {"expected": 0, "unexpected": 1, "flaky": 0, "skipped": 0, "duration": 10, "startTime": "2026-01-01T00:00:00.000Z"},
    "errors": [],
}
with open(os.path.join(step_dir, "results.json"), "w") as f:
    json.dump(results, f)
PY

  run_collector "$root"
  artifacts_dir="$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifacts_dir')"

  local attachments
  attachments="$(printf '%s' "$COLLECTOR_STDOUT" | jq -c '.failed[0].attempts[0].attachments')"

  assert_eq "0" "$COLLECTOR_RC" "exit code" &&
    assert_eq "101" "$(printf '%s' "$attachments" | jq 'length')" "all 101 candidate attachments are reported" &&
    assert_eq "100" "$(printf '%s' "$attachments" | jq '[.[] | select(.status == "usable")] | length')" "first 100 are checked and usable" &&
    assert_eq "1" "$(printf '%s' "$attachments" | jq '[.[] | select(.reason == "attachment check cap exceeded")] | length')" "exactly one attachment is capped out"
}

# --- a builder-diagnostics key with an unsafe (non-flat) name is reported
# unavailable, never written outside dest_dir ---
test_builder_diagnostics_unsafe_key_name() {
  local root artifacts_dir
  root="$(new_fixture_root)"
  trap '[ -n "${artifacts_dir:-}" ] && rm -rf "$artifacts_dir"' RETURN
  write_prowjob "$root"

  local step_dir="$root/$GCS_BASE_REL/artifacts/quay-test-e2e/artifacts"
  mkdir -p "$step_dir"
  cat >"$step_dir/results.json" <<'EOF'
{"config":{"workers":1},"suites":[{"specs":[]}],"stats":{"expected":1,"unexpected":0,"flaky":0,"skipped":0,"duration":100,"startTime":"2026-01-01T00:00:00.000Z"},"errors":[]}
EOF
  # A key with a nested path component under the builder-diagnostics prefix
  # is untrusted (GCS is a flat namespace): after stripping the prefix, the
  # name "sub/evil.txt" contains "/" and is_safe_flat_name must refuse it.
  local bd_dir="$step_dir/builder-diagnostics/sub"
  mkdir -p "$bd_dir"
  printf 'nested content\n' >"$bd_dir/evil.txt"

  run_collector "$root"
  artifacts_dir="$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.artifacts_dir')"

  assert_eq "0" "$COLLECTOR_RC" "exit code" &&
    assert_eq "unavailable" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.builder_diagnostics[0].status')" \
      "unsafe key name is reported unavailable" &&
    assert_eq "null" "$(printf '%s' "$COLLECTOR_STDOUT" | jq -r '.builder_diagnostics[0].local_path')" \
      "unsafe key name has no local_path" &&
    case "$COLLECTOR_STDERR" in
      *"skipping builder-diagnostics key with unexpected name: sub/evil.txt"*) : ;;
      *)
        echo "  expected the unsafe-name skip warning, got: $COLLECTOR_STDERR" >&2
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
