# Per-failure root cause analysis

For each entry in `failed`, perform root cause analysis:

## Read the test source

Read the failing spec file at the reported line number. The `file` and `line`
both come from `results.json`, untrusted input — resolve `file` (`realpath -m`)
against `web/playwright/e2e/` (e.g., `auth/signin.spec.ts` ->
`web/playwright/e2e/auth/signin.spec.ts`) and read it only if the resolved
path stays inside `web/playwright/e2e/`; otherwise report the path as
untrusted and do not read it.

Understand what the test does — what page it navigates to, what selectors it uses,
what API calls it makes.

Check each entry's `attempts` for the failing result's `errors` and its trace
`attachments` (the trace `url` opens in the Playwright trace viewer). Check
each attachment's validated `status` (`usable`/`redacted`/`missing`) before
treating it as available — see `references/collector-fields.md`.

## Correlate with build log

If `has_build_log` is true, search for errors around the test failure:

```bash
grep -n "Traceback\|Error\|FATAL\|FAIL\|panic:" \
  "$ARTIFACTS_DIR/build-log.txt" | head -30
```

Look for Python tracebacks, 500 responses, or infrastructure errors that coincide
with the test failure.

## Correlate with container logs

If `has_container_logs` is true, search for backend errors:

```bash
grep -n "Traceback\|Internal Server Error\|FATAL" \
  "$ARTIFACTS_DIR/container-logs/quay.log" | head -30
```

Container logs in Prow are collected via the `gather-extra` step rather than
a dedicated artifact. The collector reports the discovered usable and redacted
pod-log filenames so an unavailable log can be distinguished from a missing
prefix. They may contain Quay pod logs, operator logs, or must-gather output.

## Check Mailpit state for mail tests

When a failure involves email (confirmation, recovery, notifications), check
whether Mailpit was up. The `quay-deploy-mailpit` step sits beside the e2e
step under the workflow directory, and the collector downloads three of its
files into the `mailpit` records (each `status: "unavailable"` when the job
has no such step):

- `mailpit.build_log` (`quay-deploy-mailpit/build-log.txt`) — the rollout,
  ending in `Mailpit API reachable (HTTP 200) at <url>` when the step reached
  the API.
- `mailpit.finished` (`quay-deploy-mailpit/finished.json`) — the step's own
  `result` and `passed`.
- `mailpit.api_url` (`quay-deploy-mailpit/artifacts/mailpit_api`) — the API
  URL the tests were given. It is a record of the run, not something to fetch:
  the cluster is gone after the job.

```bash
grep -n "Mailpit API reachable\|rolled out" "$ARTIFACTS_DIR/mailpit/build-log.txt"
jq '{result, passed}' "$ARTIFACTS_DIR/mailpit/finished.json"
grep -n "\[Global Setup\] FEATURE_MAILING" "$ARTIFACTS_DIR/build-log.txt"
```

The last line is the e2e step's own view at global setup:
`[Global Setup] FEATURE_MAILING enabled, Mailpit available` or `... Mailpit
NOT available`. Only the Database-auth phase prints it, and only when
`FEATURE_MAILING` is on; LDAP and OIDC phases return before the check.
Without the collector, the same files are public objects under
`<gcs_base>/artifacts/<workflow>/quay-deploy-mailpit/` (fetch with `curl -sf`).

## Inspect Jaeger traces when present

If `has_jaeger_traces` is true, do not hand-write `jq` over the chunk files —
they can total hundreds of megabytes. Use `scripts/jaeger-extract.sh` to pull
the spans for one endpoint. The one exception is the one-trace timeline in
"Time one slow request" below, which reads one chunk at a time:

```bash
bash .agents/skills/debug-playwright-prow/scripts/jaeger-extract.sh \
  --dir "$ARTIFACTS_DIR/jaeger-traces" --endpoint 'PATTERN' \
  [--since EPOCH_SECONDS] [--until EPOCH_SECONDS] \
  [--max-files N] [--max-records N]
```

`--endpoint` is an extended regular expression matched against a span's
`http.target` tag, `http.route` tag, or `operationName` — only
`span.kind=server` spans are considered. `--since`/`--until` are a candidate
filter only; a span still must match `--endpoint` to be emitted. Temporal
overlap alone never establishes a match. Output is a single JSON array of
matching server spans (`trace_id`, `span_id`, `http_status`, `http_target`,
`http_route`, `operation_name`, `duration`, `start_time`,
`child_operations`).

Only inspect files listed in `jaeger_trace_files` under
`$ARTIFACTS_DIR/jaeger-traces/`, and correlate only matching request/trace
IDs. Otherwise, state that no valid Jaeger trace files were found; do not
invent trace findings.

## Time one slow request

To see where a slow request spent its time, read its whole trace from the
Jaeger chunks. A failed test's `server-spans.json` attachment holds only the
spans of the test's own trace id and may hold only its API calls; a registry
request from a CLI client (a push in a fixture) is its own trace, found only
in `jaeger_trace_files`.

Find the slow request by method, route and duration. `--endpoint` also
matches `operationName`, which starts with the HTTP method:

```bash
bash .agents/skills/debug-playwright-prow/scripts/jaeger-extract.sh \
  --dir "$ARTIFACTS_DIR/jaeger-traces" --endpoint '^PUT /v2/.*/blobs/uploads/' \
  --max-records 5000 >"$ARTIFACTS_DIR/slow.json"
jq -r '[.[] | select(.duration >= 10000000)] | sort_by(-.duration)[:10][]
  | [.trace_id, .span_id, .duration / 1e6, .http_status, .operation_name] | @tsv' "$ARTIFACTS_DIR/slow.json"
```

Then print that request's descendant spans as an offset timeline (seconds
from the request start, duration in ms, operation plus the table named in
`db.statement`) and flag every silent stretch longer than `GAP_S` seconds. A
trace can hold several requests (a test's API calls share one trace id), so
the timeline starts from the request's span id, not the first server span:

```bash
TRACE_ID=...   # from the lookup above
ROOT_SPAN=...  # its span_id
GAP_S=1
jq -r '.jaeger_trace_files[]' <<<"$PW_JSON" | while IFS= read -r f; do
  jq -c --arg t "$TRACE_ID" '.data[]? | select(.traceID == $t) | .spans[]' \
    "$ARTIFACTS_DIR/jaeger-traces/$f"
done | jq -rs --argjson gap "$GAP_S" --arg rid "$ROOT_SPAN" '
  def tag($k): first(.tags[]? | select(.key == $k) | .value) // null;
  def spanname: .operationName + (
    (tag("db.statement") // "" | capture("(?i)\\b(from|into|update)\\s+\"?(?<t>\\w+)").t // null)
    | if . then " " + . else "" end);
  def r3: . * 1000 | round / 1000;
  unique_by(.spanID) as $all
  | (first($all[] | select(.spanID == $rid)) // error("span \($rid) not in trace")) as $root
  | {ids: {($root.spanID): true}, n: 0}
  | until(.n == (.ids | length); .n = (.ids | length)
      | .ids as $ids | .ids += ([$all[] | select(any(.references[]?; $ids[.spanID]))
      | {(.spanID): true}] | add // {}))
  | .ids as $tree
  | [$all[] | select($tree[.spanID] and .spanID != $root.spanID)] | sort_by(.startTime) as $kids
  | "\($root.operationName)  \($root.duration / 1e6) s  status \($root | tag("http.status_code"))  trace \($root.traceID)",
    "  offset_s  dur_ms  span",
    ( foreach ($kids[], {end: true}) as $k ({prev: 0};
        if $k.end then
          ($root.duration / 1e6) as $e
          | .line = (if $e - .prev > $gap then "  GAP  \(.prev | r3) -> \($e | r3) s (end of request)" else empty end)
        else
          (($k.startTime - $root.startTime) / 1e6) as $s
          | .line = ((if $s - .prev > $gap then "  GAP  \(.prev | r3) -> \($s | r3) s\n" else "" end)
              + "  \($s | r3)  \($k.duration / 1000)  \($k | spanname)")
          | .prev = ([.prev, $s + $k.duration / 1e6] | max)
        end;
        .line) )'
```

Each chunk is read on its own, so memory stays bounded by the largest chunk.
A `GAP` line is time the request spent outside every instrumented call.

What the spans cannot show: only Flask (the server span) and psycopg2 (the
SQL child spans) are instrumented. Redis, lock acquisition and storage I/O
emit no spans, so a gap is unexplained time, not proof of any one cause.
Lock contention can only be inferred from a gap's position and length (for
example a gap close to a lock's TTL between two lookups of the same row).
The direct evidence is the Quay pod log, on code that logs lock timeouts:

```bash
grep -n "Timed out acquiring blob lock\|GC worker holds BLOB_DELETE_\|Could not acquire lock for blob" \
  "$ARTIFACTS_DIR/container-logs/quay.log"
```

Zero hits mean nothing on a build without those log lines; check the run's
source (`provenance.source_clone_sha`) with `git grep` for the message before
reading absence as "no contention". Match a hit to the slow request by digest
and timestamp.

## Determine auth phase

Check the test's `tags` for `auth:OIDC` or `auth:LDAP`. Tests without auth-specific
tags run in the DB auth phase (the first phase).

## Classify and explain

For each failure, classify the root cause and explain conversationally:
- **Selector change** — element not found but backend responded fine
- **Backend error** — 500/traceback in container logs or build log errors
- **Timing/race** — intermittent, slow responses, or missing `waitFor`
- **Auth/config** — failure only in one auth phase, related to auth swap
- **Test isolation** — leftover state from prior tests causing interference
- **Infra** — browser crash, connection refused, worker timeout, pod scheduling

For each one, state what the test was trying to do, what went wrong, what the
build/container logs show, and what a fix would look like.
