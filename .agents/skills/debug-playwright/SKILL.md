---
name: debug-playwright
description: >
  Debug Playwright E2E test failures from GitHub Actions CI runs.
  Downloads artifacts, categorizes failures (flaky/real/infra),
  correlates with backend logs and Jaeger traces, and offers fixes.
argument-hint: PR_NUMBER | RUN_URL
allowed-tools:
  - Bash(bash scripts/playwright-debug.sh *)
  - Bash(gh run view *)
  - Bash(gh run download *)
  - Bash(gh pr view *)
  - Read
  - Grep
  - Edit
  - AskUserQuestion
---

# Debug Playwright CI Failures

Debug Playwright test failures for `$ARGUMENTS`.

## Step 1: Fetch and Categorize

```bash
bash scripts/playwright-debug.sh $ARGUMENTS
```

Capture the full JSON output, then extract `artifacts_dir` for use in later commands:

```bash
PW_JSON=$(bash scripts/playwright-debug.sh $ARGUMENTS)
ARTIFACTS_DIR=$(echo "$PW_JSON" | jq -r '.artifacts_dir')
```

Key fields:
- `artifacts_dir` — temp directory with downloaded artifacts
- `failed` — tests that failed on all attempts (real failures), includes `error_message`, `error_stack`, `last_step`, and `attachments`
- `flaky` — tests that failed then passed on retry
- `interrupted` — tests where a worker crashed
- `stats` — overall run statistics
- `surge_url` — link to the HTML report
- `has_container_logs` / `has_jaeger_traces` — what extra data is available
- `global_setup_failure` — if true, no tests ran at all (check `errors` field)

If exit code is 2, the run is still in progress — tell the user to wait or use `/dev:poll`.

## Step 2: Report Overview

Summarize what happened conversationally:
- Total tests, pass/fail/flaky counts
- Link to the Surge HTML report (if available)
- List flaky tests briefly (name + file) — note them but don't deep-dive unless asked
- Note any interrupted tests (worker crashes)

If `global_setup_failure` is true, report the setup errors and stop.

If there are no real failures, report "all failures were flaky" with the list and stop.

## Step 3: Diagnose Each Real Failure

For each entry in `failed`, perform root cause analysis:

### 3a: Read the test source

Read the failing spec file at the reported line number. The file path from the JSON
is relative to `web/playwright/e2e/` — resolve it against the quay/quay repo root
(e.g., `auth/signin.spec.ts` → `web/playwright/e2e/auth/signin.spec.ts`).

Understand what the test does — what page it navigates to, what selectors it uses,
what API calls it makes.

Check `last_step` from the JSON — this tells you which Playwright action timed out
(e.g., `locator.click("button.submit")`).

### 3b: Correlate with container logs

If `has_container_logs` is true, search for backend errors within a ~30-second
window around the test's `startTime`:

```bash
grep -n "Traceback\|Internal Server Error\|FATAL" \
  "$ARTIFACTS_DIR/quay-container-logs/quay-quay.log" | head -30
```

Look for Python tracebacks, 500 responses, or gunicorn crashes that coincide
with the test failure.

### 3c: Correlate with Jaeger traces

If `has_jaeger_traces` is true, infer the API endpoint from the test source
(e.g., a test navigating to `/organization/myorg/teams` likely hits
`GET /api/v1/organization/.*/team`). Search for matching spans:

```bash
jq '[.data[].spans[] | select(.operationName | test("ENDPOINT_PATTERN")) |
  {operationName, duration, tags: [.tags[] |
  select(.key == "http.status_code" or .key == "error")]}]' \
  "$ARTIFACTS_DIR/jaeger-traces/traces.json"
```

Look for slow spans, error spans, and 4xx/5xx status codes.

### 3d: Determine auth phase

Check the test's `tags` for `auth:OIDC` or `auth:LDAP`. Tests without auth-specific
tags run in the DB auth phase (the first phase).

## Step 4: Classify and Explain

For each failure, classify the root cause and explain conversationally:
- **Selector change** — element not found but backend responded fine
- **Backend error** — 500/traceback in container logs or error spans in traces
- **Timing/race** — intermittent, slow spans in traces, or missing `waitFor`
- **Auth/config** — failure only in one auth phase, related to auth swap
- **Test isolation** — leftover state from prior tests causing interference
- **Infra** — browser crash, connection refused, worker timeout

For each one, state what the test was trying to do, what went wrong, what the
backend logs/traces show, and what a fix would look like.

## Step 5: Offer Fixes

Ask: "Want me to apply fixes for any of these?"

If yes, edit the spec files under `web/playwright/e2e/`. Show what you're changing
and why. Only edit backend code if the user explicitly asks.

Do NOT auto-commit — let the user review the changes.

## Cleanup

When diagnosis is complete, remove the temp artifacts directory:

```bash
rm -rf "$ARTIFACTS_DIR"
```
