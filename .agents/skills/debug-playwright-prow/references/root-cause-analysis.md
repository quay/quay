# Per-failure root cause analysis

For each entry in `failed`, perform root cause analysis:

## Read the test source

Read the failing spec file at the reported line number. The `file` and `line`
both come from `results.json`. The file path is relative to `web/playwright/e2e/`
— resolve it against the quay/quay repo root (e.g., `auth/signin.spec.ts` ->
`web/playwright/e2e/auth/signin.spec.ts`).

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

## Inspect Jaeger traces when present

If `has_jaeger_traces` is true, do not hand-write `jq` over the chunk files —
they can total hundreds of megabytes. Use `scripts/jaeger-extract.sh` to pull
the spans for one endpoint:

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
