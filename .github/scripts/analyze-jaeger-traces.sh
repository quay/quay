#!/usr/bin/env bash
set -euo pipefail

TRACES_FILE="${TRACES_FILE:-jaeger-traces/traces.json}"
METRICS_FILE="${METRICS_FILE:-jaeger-traces/trace-metrics.json}"
COMMIT_SHA="${COMMIT_SHA:-unknown}"

if [[ ! -f "$TRACES_FILE" ]] || [[ ! -s "$TRACES_FILE" ]]; then
  echo "::warning::Jaeger traces file not found or empty — skipping analysis"
  exit 0
fi

if ! jq -e '.data' "$TRACES_FILE" > /dev/null 2>&1; then
  echo "::warning::Jaeger traces file is not valid JSON — skipping analysis"
  exit 0
fi

total_traces=$(jq '.data | length' "$TRACES_FILE")
total_spans=$(jq '[.data[].spans[]] | length' "$TRACES_FILE")

if [[ "$total_spans" -eq 0 ]]; then
  echo "::warning::No spans found in Jaeger traces — skipping analysis"
  exit 0
fi

# ── Check 1: Error spans (5xx and exception-only, excluding expected 4xx) ──
error_spans_json=$(jq '[.data[] as $trace | $trace.spans[] |
  select(
    any(.tags[]; .key == "otel.status_code" and .value == "ERROR")
    or any(.tags[]; .key == "error" and (.value == true))
  ) |
  ([.tags[] | select(.key == "http.status_code") | .value | tonumber] | first // 500) as $status |
  select($status >= 500) |
  {
    operation: .operationName,
    status: $status,
    message: (([.tags[] | select(.key == "otel.status_description" or .key == "exception.message") | .value] | first) // ""),
    trace_id: $trace.traceID
  }
]' "$TRACES_FILE")

error_count=$(echo "$error_spans_json" | jq 'length')

# ── Check 2: Operation name cardinality ──
unique_ops=$(jq '[.data[].spans[].operationName] | unique | length' "$TRACES_FILE")

# ── Check 3: Orphaned spans ──
orphaned_count=$(jq '[.data[] |
  (.spans | map(.spanID)) as $ids |
  .spans[] |
  select(
    any(.references[]?; .refType == "CHILD_OF" and (.spanID as $pid | $ids | any(. == $pid) | not))
  )
] | length' "$TRACES_FILE")

# ── Check 4: Slow DB queries (>500ms = >500000µs) ──
slow_queries_json=$(jq '[.data[] as $trace | $trace.spans[] |
  select(any(.tags[]; .key == "db.system") and .duration > 500000) |
  {
    operation: .operationName,
    duration_ms: ((.duration / 1000) | round),
    statement: (([.tags[] | select(.key == "db.statement") | .value[:80]] | first) // ""),
    trace_id: $trace.traceID
  }
]' "$TRACES_FILE")

slow_count=$(echo "$slow_queries_json" | jq 'length')

# ── Check 5: Service name presence ──
has_quay=$(jq '[.data[].processes | to_entries[].value.serviceName] | any(. == "quay")' "$TRACES_FILE")

# ── Emit warnings ──
if [[ "$error_count" -gt 0 ]]; then
  echo "::warning::Jaeger: ${error_count} error span(s) detected (5xx / exceptions)"
fi
if [[ "$unique_ops" -gt 100 ]]; then
  echo "::warning::Jaeger: operation name cardinality is ${unique_ops} (possible parameter leakage in span names)"
fi
if [[ "$orphaned_count" -gt 0 ]]; then
  echo "::warning::Jaeger: ${orphaned_count} orphaned span(s) (broken trace context propagation)"
fi
if [[ "$slow_count" -gt 0 ]]; then
  echo "::warning::Jaeger: ${slow_count} slow DB query/queries (>500ms)"
fi
if [[ "$has_quay" != "true" ]]; then
  echo "::warning::Jaeger: service 'quay' not found in traces — tracing may not be configured"
fi

# ── GitHub Step Summary ──
{
  echo "## Jaeger Trace Analysis"
  echo ""
  echo "| Metric | Value |"
  echo "|--------|-------|"
  echo "| Total traces | ${total_traces} |"
  echo "| Total spans | ${total_spans} |"
  echo "| Error spans | ${error_count} |"
  echo "| Orphaned spans | ${orphaned_count} |"
  echo "| Unique operations | ${unique_ops} |"
  echo "| Slow DB queries (>500ms) | ${slow_count} |"

  if [[ "$error_count" -gt 0 ]]; then
    echo ""
    echo "### Error Spans"
    echo ""
    echo "| Operation | Status | Message | Trace ID |"
    echo "|-----------|--------|---------|----------|"
    echo "$error_spans_json" | jq -r '.[:20][] | "| `\(.operation)` | \(.status) | \(.message[:60]) | `\(.trace_id[:12])...` |"'
  fi

  if [[ "$slow_count" -gt 0 ]]; then
    echo ""
    echo "### Slow DB Queries (>500ms)"
    echo ""
    echo "| Operation | Duration | Statement | Trace ID |"
    echo "|-----------|----------|-----------|----------|"
    echo "$slow_queries_json" | jq -r '.[:20][] | "| `\(.operation)` | \(.duration_ms)ms | `\(.statement[:40])` | `\(.trace_id[:12])...` |"'
  fi

  echo ""
  echo "### Structural Checks"
  echo ""
  echo "| Check | Result |"
  echo "|-------|--------|"

  if [[ "$has_quay" == "true" ]]; then
    echo "| Service 'quay' present | pass |"
  else
    echo "| Service 'quay' present | **fail** |"
  fi

  if [[ "$orphaned_count" -eq 0 ]]; then
    echo "| Orphaned spans | pass (0) |"
  else
    echo "| Orphaned spans | **warn** (${orphaned_count}) |"
  fi

  if [[ "$unique_ops" -le 100 ]]; then
    echo "| Operation cardinality < 100 | pass (${unique_ops}) |"
  else
    echo "| Operation cardinality < 100 | **warn** (${unique_ops}) |"
  fi

  if [[ "$slow_count" -eq 0 ]]; then
    echo "| Slow DB queries | pass (0) |"
  else
    echo "| Slow DB queries | **warn** (${slow_count}) |"
  fi
} >> "${GITHUB_STEP_SUMMARY:-/dev/null}"

# ── Baseline metrics JSON ──
error_summary=$(echo "$error_spans_json" | jq 'group_by(.operation) | map({operation: .[0].operation, count: length, status: .[0].status})')
slow_summary=$(echo "$slow_queries_json" | jq '[.[] | {operation, duration_ms, trace_id}]')

jq -n \
  --arg commit "$COMMIT_SHA" \
  --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --argjson total_traces "$total_traces" \
  --argjson total_spans "$total_spans" \
  --argjson error_spans "$error_count" \
  --argjson orphaned_spans "$orphaned_count" \
  --argjson unique_operations "$unique_ops" \
  --argjson slow_db_queries "$slow_count" \
  --argjson errors "$error_summary" \
  --argjson slow_queries "$slow_summary" \
  '{
    schema_version: 1,
    generated_at: $timestamp,
    commit_sha: $commit,
    summary: {
      total_traces: $total_traces,
      total_spans: $total_spans,
      error_spans: $error_spans,
      orphaned_spans: $orphaned_spans,
      unique_operations: $unique_operations,
      slow_db_queries: $slow_db_queries
    },
    errors: $errors,
    slow_queries: $slow_queries
  }' > "$METRICS_FILE"

echo "Trace metrics written to $METRICS_FILE"
