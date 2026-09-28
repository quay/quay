#!/bin/bash
# jaeger-extract.sh -- Correlate one request across a Prow run's Jaeger chunk
# files without hand-writing jq over hundreds of megabytes of trace JSON.
#
# Usage:
#   bash .agents/skills/debug-playwright-prow/scripts/jaeger-extract.sh \
#     --dir JAEGER_TRACES_DIR --endpoint PATTERN \
#     [--since EPOCH_SECONDS] [--until EPOCH_SECONDS] \
#     [--max-files N] [--max-records N]
#
# --dir       the collector's <work_dir>/jaeger-traces, holding
#             traces.json and/or traces-1.json ... traces-N.json.
# --endpoint  an extended regular expression (jq test/1 syntax). Matching is
#             non-negotiable: a span matches only when this pattern matches
#             one of its endpoint / request identifiers -- the http.target
#             tag (e.g. /api/v1/superuser/<uuid>/build), the http.route tag
#             (e.g. /api/v1/superuser/<build_uuid>/build), or operationName
#             (e.g. "GET /api/v1/superuser/<build_uuid>/build"). Only
#             span.kind=server spans are considered.
# --since / --until
#             optional epoch-seconds bounds on span start time. These are a
#             CANDIDATE FILTER ONLY: a span still must match --endpoint to be
#             emitted. Temporal overlap alone never establishes a match.
# --max-files    cap on the number of chunk files read (default 100).
# --max-records  cap on the number of matching spans emitted (default 500).
#
# Output (stdout): a single JSON array, one record per matching server span:
#   trace_id, span_id, http_status, http_target, http_route, operation_name,
#   duration, start_time, and child_operations -- a count of that trace's
#   other spans grouped by operation name (not every child span).
#
# A chunk file that is not valid JSON is skipped with a stderr warning; the
# run continues. Exceeding --max-files or --max-records truncates with a
# stderr warning rather than failing.
#
# Exit codes:
#   0 -- ran successfully (possibly zero matches)
#   1 -- usage error, missing/unreadable --dir, or no chunk files found
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: jaeger-extract.sh --dir DIR --endpoint PATTERN [--since EPOCH_SECONDS] [--until EPOCH_SECONDS] [--max-files N] [--max-records N]
EOF
}

DIR=""
ENDPOINT=""
SINCE=""
UNTIL=""
MAX_FILES=100
MAX_RECORDS=500

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dir)
      DIR="${2:?--dir requires a value}"
      shift 2
      ;;
    --endpoint)
      ENDPOINT="${2:?--endpoint requires a value}"
      shift 2
      ;;
    --since)
      SINCE="${2:?--since requires a value}"
      shift 2
      ;;
    --until)
      UNTIL="${2:?--until requires a value}"
      shift 2
      ;;
    --max-files)
      MAX_FILES="${2:?--max-files requires a value}"
      shift 2
      ;;
    --max-records)
      MAX_RECORDS="${2:?--max-records requires a value}"
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

[ -n "$DIR" ] || {
  echo "ERROR: --dir is required" >&2
  usage
  exit 1
}
[ -n "$ENDPOINT" ] || {
  echo "ERROR: --endpoint is required" >&2
  usage
  exit 1
}
[ -d "$DIR" ] || {
  echo "ERROR: not a directory: $DIR" >&2
  exit 1
}

# A bad --endpoint regex makes every per-file jq call below fail, which is
# caught and skipped as a per-file warning -- so an invalid pattern would
# otherwise read as "zero matching spans" instead of a usage error.
if ! endpoint_err=$(jq -n --arg pat "$ENDPOINT" '"" | test($pat)' 2>&1 >/dev/null); then
  echo "ERROR: --endpoint is not a valid regular expression: $ENDPOINT" >&2
  echo "  $endpoint_err" >&2
  exit 1
fi

is_uint() { [[ "$1" =~ ^[0-9]+$ ]]; }

SINCE_US="null"
if [ -n "$SINCE" ]; then
  is_uint "$SINCE" || {
    echo "ERROR: --since must be an integer epoch-seconds value" >&2
    exit 1
  }
  SINCE_US=$((SINCE * 1000000))
fi

UNTIL_US="null"
if [ -n "$UNTIL" ]; then
  is_uint "$UNTIL" || {
    echo "ERROR: --until must be an integer epoch-seconds value" >&2
    exit 1
  }
  UNTIL_US=$((UNTIL * 1000000))
fi

is_uint "$MAX_FILES" || {
  echo "ERROR: --max-files must be a non-negative integer" >&2
  exit 1
}
is_uint "$MAX_RECORDS" || {
  echo "ERROR: --max-records must be a non-negative integer" >&2
  exit 1
}

mapfile -t CHUNK_FILES < <(find "$DIR" -maxdepth 1 -type f \( -name 'traces.json' -o -name 'traces-*.json' \) | sort -V)
if [ "${#CHUNK_FILES[@]}" -eq 0 ]; then
  echo "ERROR: no traces.json or traces-*.json chunk files found under $DIR" >&2
  exit 1
fi

TOTAL_FILES="${#CHUNK_FILES[@]}"
if [ "$TOTAL_FILES" -gt "$MAX_FILES" ]; then
  echo "WARNING: found $TOTAL_FILES chunk files, reading only the first $MAX_FILES (--max-files)" >&2
  CHUNK_FILES=("${CHUNK_FILES[@]:0:$MAX_FILES}")
fi

# --- Scratch storage: repo tmp/, never system /tmp ---
if REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null); then
  :
else
  REPO_ROOT="$PWD"
  echo "WARNING: not inside a git work tree; using \$PWD ($REPO_ROOT) as the repo root for scratch storage" >&2
fi
mkdir -p "$REPO_ROOT/tmp"
RECORDS_FILE=$(mktemp "$REPO_ROOT/tmp/jaeger-extract.XXXXXX")
trap 'rm -f "$RECORDS_FILE"' EXIT

# Matching rule (non-negotiable): a span matches only via its endpoint /
# request identifiers. A time window (applied below via $since/$until) is a
# candidate filter only and never substitutes for the endpoint match.
JQ_FILTER='
  limit($remaining;
    .data[]? as $trace
    | ($trace.spans // []) as $spans
    | $spans[] as $span
    | (reduce ($span.tags // [])[] as $t ({}; .[$t.key] = $t.value)) as $tagmap
    | select($tagmap["span.kind"] == "server")
    | ($tagmap["http.target"]) as $target
    | ($tagmap["http.route"]) as $route
    | ($span.operationName) as $op
    | select(
        (($target != null) and ($target | test($pat))) or
        (($route  != null) and ($route  | test($pat))) or
        (($op     != null) and ($op     | test($pat)))
      )
    | select($since == null or ($span.startTime >= $since))
    | select($until == null or ($span.startTime <= $until))
    | {
        trace_id: $span.traceID,
        span_id: $span.spanID,
        http_status: ($tagmap["http.status_code"] // null),
        http_target: $target,
        http_route: $route,
        operation_name: $op,
        duration: $span.duration,
        start_time: $span.startTime,
        child_operations: (
          [ $spans[] | select(.spanID != $span.spanID) | .operationName ]
          | group_by(.)
          | map({operation: .[0], count: length})
        )
      }
  )
'

for file in "${CHUNK_FILES[@]}"; do
  if ! jq -e . "$file" >/dev/null 2>&1; then
    echo "WARNING: skipping invalid JSON chunk file: $file" >&2
    continue
  fi
  before=$(wc -l <"$RECORDS_FILE" | tr -d ' ')
  remaining=$(( MAX_RECORDS - before ))
  if [ "$remaining" -le 0 ]; then
    echo "WARNING: reached --max-records ($MAX_RECORDS); stopping early before $file" >&2
    break
  fi
  if ! jq -c --arg pat "$ENDPOINT" --argjson since "$SINCE_US" --argjson until "$UNTIL_US" --argjson remaining "$(( remaining + 1 ))" \
    "$JQ_FILTER" "$file" >>"$RECORDS_FILE"; then
    echo "WARNING: jq failed while scanning $file; skipping" >&2
    continue
  fi
  added=$(( $(wc -l <"$RECORDS_FILE" | tr -d ' ') - before ))
  if [ "$added" -gt "$remaining" ]; then
    head -n "$(( before + remaining ))" "$RECORDS_FILE" >"$RECORDS_FILE.tmp" && mv "$RECORDS_FILE.tmp" "$RECORDS_FILE"
    echo "WARNING: reached --max-records ($MAX_RECORDS); output capped while scanning $file" >&2
    break
  fi
done

jq -s '.' "$RECORDS_FILE"
