# shellcheck shell=bash
# collector-lib.sh -- sourceable pure functions shared by playwright-debug-prow.sh.
#
# No top-level executing code and no `set -euo pipefail` of its own: the
# caller (the main script, or a test runner) owns the shell mode. Functions
# here may reference config constants (e.g. CURL_TIMEOUT, CURL_MAXSIZE) that
# are defined by the caller, not by this file.
#
# The globals these functions set (e.g. PLAYWRIGHT_SHA, JOB_RESULT_REASON)
# are consumed by the sourcing caller, not within this file.
# shellcheck disable=SC2034

json_array() {
  if [ "$#" -eq 0 ]; then
    printf '[]'
  else
    printf '%s\n' "$@" | jq -R . | jq -s .
  fi
}

# Like json_array, but each argument is already a JSON value (e.g. an object
# built with jq -nc), not a raw string to be quoted.
json_object_array() {
  if [ "$#" -eq 0 ]; then
    printf '[]'
  else
    printf '%s\n' "$@" | jq -s .
  fi
}

# Derive the ci-operator sparse source clone SHA/ref from clone-records.json.
# The first array element is a placeholder with empty refs and no final_sha
# and must be skipped; the clone of interest is the last element with a
# non-empty org/repo. Sets SOURCE_CLONE_SHA(_REASON) and SOURCE_CLONE_REF(_REASON).
parse_clone_records() {
  local path="$1"
  SOURCE_CLONE_SHA=""
  SOURCE_CLONE_SHA_REASON=""
  SOURCE_CLONE_REF=""
  SOURCE_CLONE_REF_REASON=""

  if [ -z "$path" ] || [ ! -s "$path" ]; then
    SOURCE_CLONE_SHA_REASON="clone-records.json was not downloaded"
    SOURCE_CLONE_REF_REASON="clone-records.json was not downloaded"
    return
  fi

  local entry jq_rc=0
  entry=$(jq -c '[.[] | select((.refs.org // "") != "" and (.refs.repo // "") != "")] | last // empty' "$path" 2>/dev/null) || jq_rc=$?
  if [ "$jq_rc" -ne 0 ]; then
    SOURCE_CLONE_SHA_REASON="clone-records.json could not be parsed as the expected shape (array of clone records)"
    SOURCE_CLONE_REF_REASON="clone-records.json could not be parsed as the expected shape (array of clone records)"
    return
  fi
  if [ -z "$entry" ] || [ "$entry" = "null" ]; then
    SOURCE_CLONE_SHA_REASON="clone-records.json has no element with non-empty refs.org and refs.repo"
    SOURCE_CLONE_REF_REASON="clone-records.json has no element with non-empty refs.org and refs.repo"
    return
  fi

  SOURCE_CLONE_SHA=$(printf '%s' "$entry" | jq -r '.final_sha // empty')
  if [ -z "$SOURCE_CLONE_SHA" ]; then
    SOURCE_CLONE_SHA_REASON="matched clone-records.json element has no final_sha"
  fi

  SOURCE_CLONE_REF=$(printf '%s' "$entry" | jq -r '.refs.base_ref // empty')
  if [ -z "$SOURCE_CLONE_REF" ]; then
    SOURCE_CLONE_REF_REASON="matched clone-records.json element has no refs.base_ref"
  fi
}

# Derive the build-root Prow job's overall result, and a base_ref fallback,
# from finished.json. Sets JOB_RESULT(_REASON) and FINISHED_REVISION.
parse_finished() {
  local path="$1"
  JOB_RESULT=""
  JOB_RESULT_REASON=""
  FINISHED_REVISION=""

  if [ -z "$path" ] || [ ! -s "$path" ]; then
    JOB_RESULT_REASON="finished.json was not downloaded"
    return
  fi

  local jq_rc=0
  JOB_RESULT=$(jq -r '.result // empty' "$path" 2>/dev/null) || jq_rc=$?
  if [ "$jq_rc" -ne 0 ]; then
    JOB_RESULT=""
    JOB_RESULT_REASON="finished.json could not be parsed as the expected shape (JSON object with .result)"
    return
  fi
  if [ -z "$JOB_RESULT" ]; then
    JOB_RESULT_REASON="finished.json has no .result field"
  fi

  FINISHED_REVISION=$(jq -r '.revision // empty' "$path" 2>/dev/null)
}

# Extract the Playwright suite's actual source SHA from the e2e step's own
# build log. This is distinct from source_clone_sha (ci-operator's sparse
# source clone, set by parse_clone_records), which can legitimately differ
# from the commit Playwright actually ran from. Format:
#   PLAYWRIGHT_SOURCE_PROVENANCE repo=<repo> ref=<ref> sha=<sha|unknown>
# Sets PLAYWRIGHT_SHA(_REASON).
parse_playwright_sha() {
  local path="$1"
  PLAYWRIGHT_SHA=""
  PLAYWRIGHT_SHA_REASON=""

  if [ -z "$path" ] || [ ! -s "$path" ]; then
    PLAYWRIGHT_SHA_REASON="step build log was not downloaded"
    return
  fi

  local line
  line=$(sed -E 's/\x1b\[[0-9;]*m//g' "$path" | grep -F 'PLAYWRIGHT_SOURCE_PROVENANCE' | tail -1 || true)
  if [ -z "$line" ]; then
    PLAYWRIGHT_SHA_REASON="step build log has no PLAYWRIGHT_SOURCE_PROVENANCE line (this CI step predates it)"
    return
  fi

  local sha
  sha=$(printf '%s' "$line" | grep -oP 'PLAYWRIGHT_SOURCE_PROVENANCE\s+repo=\S*\s+ref=\S*\s+sha=\K\S+' || true)
  if [ -z "$sha" ]; then
    PLAYWRIGHT_SHA_REASON="PLAYWRIGHT_SOURCE_PROVENANCE line present but repo=/ref=/sha= fields could not be parsed in order"
    return
  fi
  if [ "$sha" = "unknown" ]; then
    PLAYWRIGHT_SHA_REASON="step printed sha=unknown (archive fallback, no git metadata)"
    return
  fi

  PLAYWRIGHT_SHA="$sha"
}

# Classifies already-read content as "redacted" or "usable" against the CI
# sensitive-content placeholder (the same text checked for redacted pod logs
# and attachments in playwright-debug-prow.sh). Kept separate from
# classify_object_head's network read so it can be exercised directly
# against local bytes without a network run.
classify_bytes() {
  if grep -Fqx 'This file contained potentially sensitive information and has been removed.' <<<"$1"; then
    printf 'redacted'
  else
    printf 'usable'
  fi
}

# Reads only the first 256 bytes of a GCS object via a curl range request and
# classifies it -- an intact trace/report blob can be megabytes and there can
# be many, so this never downloads one in full just to classify it. A HEAD
# check first distinguishes an object that was never produced (workflow step
# didn't run, "not_found") from one whose HEAD probe itself failed for some
# other reason ("head_failed") and from one that exists but whose range read
# failed ("missing") -- each caller decides how to report the middle case.
classify_object_head() {
  local url="$1"
  local http_code
  http_code=$(curl -sL "${CURL_TIMEOUT[@]}" --head -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || true)
  if [ "$http_code" = "404" ]; then
    printf 'not_found'
    return
  elif [ "$http_code" != "200" ]; then
    printf 'head_failed'
    return
  fi
  local head
  if ! head=$(curl -sfL "${CURL_TIMEOUT[@]}" "${CURL_MAXSIZE[@]}" -r 0-255 "$url" 2>/dev/null); then
    printf 'missing'
    return
  fi
  classify_bytes "$head"
}

# Bounded preview of a downloaded diagnostics file: at most 40 lines,
# ANSI-stripped, each truncated to 500 characters -- a preview for triage,
# never the whole file.
first_lines_json() {
  local path="$1"
  # `|| true`: under pipefail, sed/cut can receive SIGPIPE (exit 141) once
  # `head -n 40` stops reading a file with more than 40 lines; that is not a
  # real failure of this pipeline.
  sed -E 's/\x1b\[[0-9;]*m//g' "$path" | head -n 40 | cut -c1-500 | jq -R . | jq -s . || true
}

# Prints the evidence-gap JSON record for must-gather.tar's classify_object_head
# status, or nothing when that status records no gap: intact-but-over-cap and
# never-ran must never produce a gap record.
must_gather_gap_record() {
  local status="$1" url="$2"
  case "$status" in
    redacted)
      jq -nc --arg url "$url" '{artifact: "must-gather.tar", source_url: $url, status: "redacted", reason: "CI sensitive-content placeholder"}'
      ;;
    missing)
      jq -nc --arg url "$url" '{artifact: "must-gather.tar", source_url: $url, status: "missing", reason: "range read failed"}'
      ;;
    head_failed)
      jq -nc --arg url "$url" '{artifact: "must-gather.tar", source_url: $url, status: "missing", reason: "HEAD probe failed"}'
      ;;
  esac
}

# Listed object names are untrusted data (GCS is a flat namespace, so a
# key can contain "/" or ".." segments); only a flat, single-component
# name is trusted as a filesystem path, matching the allowlist gate the
# download loops in playwright-debug-prow.sh use for their derived names.
is_safe_flat_name() {
  local name="$1"
  if [ "$name" = "." ] || [ "$name" = ".." ] || [[ "$name" == */* ]] || [[ ! "$name" =~ ^[A-Za-z0-9._-]+$ ]]; then
    return 1
  fi
  return 0
}
