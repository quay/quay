# E2E Coverage Measurement for Playwright Tests

## Context

We want to measure which parts of Quay are actually exercised by our 70+ Playwright E2E tests. This is different from traditional code coverage — we're not measuring lines hit, but answering: **which API endpoints and UI paths do our E2E tests actually cover?**

The key insight from research: **Jaeger/OTEL tracing is already running with 100% sample rate during CI E2E tests** (`local-dev/jaeger/jaeger-config.yaml` sets `sample_rate: 1.0`). Every API request from every Playwright test is already captured as a trace span with `http.method`, `http.route`, and `http.status_code`. The data already exists — we just need to analyze it.

**Coverport** (Konflux) is Go-specific (uses `go build -cover` + GOCOVERDIR) — not applicable to our Python/React stack.

---

## Phase 1: API Endpoint Coverage from Jaeger Traces

**Status:** Implemented
**Effort:** ~1 day
**Value:** Very high
**Dependencies:** None — data already exists
**PR scope:** Single PR

### What it delivers

A report showing which Flask API routes were exercised during E2E tests vs. the full set of registered routes. Answers: "Which API endpoints have zero E2E test coverage?"

### How it works

1. After E2E tests complete, traces are already exported to `jaeger-traces/traces.json` (line 157 of `web-playwright-ci.yaml`)
2. A new Python script extracts unique `(http.method, http.route)` tuples from the Jaeger spans
3. The script fetches the complete route list from Quay's `/api/v1/discovery?internal=true` endpoint (which calls `app.url_map.iter_rules()` via `endpoints/api/discovery.py`)
4. For V2 registry routes, the script enumerates the known routes from `endpoints/v2/` (blob, manifest, catalog, tag, referrers, v2auth)
5. The script produces: coverage percentage, covered routes, uncovered routes, and a status-code matrix

### Files to create/modify

**New: `.github/scripts/analyze-api-coverage.py`**
- Reads `jaeger-traces/traces.json` (Jaeger API format: `.data[].spans[].tags[]`)
- Extracts `(http.method, http.route, http.status_code)` from span tags set by `opentelemetry-instrumentation-flask` (FlaskInstrumentor in `app.py:381`)
- Fetches complete route catalog from `http://localhost:8080/api/v1/discovery?internal=true`
- V2 routes are hardcoded (stable set: `/v2/`, blob, manifest, catalog, tag, referrers, v2auth patterns)
- Outputs JSON report + GitHub Step Summary markdown table
- No external dependencies — uses only stdlib `json`, `urllib`

**Modify: `.github/workflows/web-playwright-ci.yaml`**
- Add step after "Analyze Jaeger traces" (around line 163):
  ```yaml
  - name: Analyze API endpoint coverage
    if: always()
    continue-on-error: true
    run: python3 .github/scripts/analyze-api-coverage.py
    env:
      TRACES_FILE: jaeger-traces/traces.json
      QUAY_API_URL: http://localhost:8080
  ```
- Include `api-coverage.json` in the existing `jaeger-traces/` artifact upload

### Output format (GitHub Step Summary)

```markdown
## API Endpoint Coverage

| Metric | Value |
|--------|-------|
| Total API routes | 142 |
| Exercised by E2E tests | 87 |
| Coverage | 61.3% |

### Uncovered Routes
| Method | Route | Tag |
|--------|-------|-----|
| POST | /api/v1/repository/{repository}/build/ | build |
| DELETE | /api/v1/organization/{orgname}/logs | logs |

### Status Code Matrix (Top 20)
| Method | Route | Status Codes Seen |
|--------|-------|-------------------|
| GET | /api/v1/repository/{repository} | 200, 404 |
| POST | /api/v1/repository | 201, 400 |
```

### Risks & mitigations

- **Jaeger trace limit:** Current curl uses `limit=1000`. With 70+ test files making many API calls, this may truncate. **Fix:** Increase to `limit=5000` or query multiple pages.
- **Span attribute names:** OTEL Flask instrumentation sets `http.route` (the Flask URL rule pattern, not the concrete URL). If `http.route` is missing on some spans, fall back to parsing `http.target` or `operationName`. Need to verify actual attribute names from a real trace export.
- **Two-phase execution:** DB auth and OIDC auth phases both write traces. Since Jaeger aggregates all traces, the single export captures both phases automatically.
- **V2 registry routes:** These run in a separate gunicorn process (`gunicorn-registry`) with a different service name. Verify the Jaeger export includes spans from both services, or make a second query for the registry service.

### Verification

1. Run E2E tests locally with Jaeger (`make local-dev-up` with jaeger config merged)
2. Export traces: `curl -sf "http://localhost:16686/api/traces?service=quay&limit=5000" -o traces.json`
3. Inspect a span to confirm `http.route` and `http.method` tags are present
4. Run the analysis script against the exported traces
5. Verify the uncovered routes list makes sense (e.g., build endpoints should be uncovered since no build tests exist)

---

## Phase 2: Frontend V8 Coverage via Monocart Reporter

**Status:** Not started
**Effort:** ~2-3 days
**Value:** Medium
**Dependencies:** `monocart-coverage-reports` npm package
**PR scope:** Single PR

### What it delivers

Line/branch/function coverage of the React/TypeScript frontend code as exercised by E2E tests, uploaded to Codecov with `e2e-frontend` flag.

### Why this approach

Shows which UI components and code paths are never rendered during E2E tests. The V8 approach requires no build changes — Playwright collects coverage natively from Chromium. No Istanbul build instrumentation needed.

### How it works

Monocart Coverage Reports is a Playwright-compatible reporter that automatically calls `page.coverage.startJSCoverage()` / `stopJSCoverage()` per test, converts V8 coverage to Istanbul format using source maps, and generates LCOV output.

### Files to create/modify

**Modify: `web/package.json`**
- Add devDependency: `monocart-coverage-reports`

**Modify: `web/playwright.config.ts`**
- Add monocart reporter alongside existing reporters:
  ```ts
  ['monocart-coverage-reports', {
    name: 'E2E Coverage',
    outputDir: 'coverage/e2e',
    sourceFilter: (sourcePath) => sourcePath.includes('/src/'),
    reports: ['lcovonly', 'v8'],
  }]
  ```

**Modify: `.github/workflows/web-playwright-ci.yaml`**
- Challenge: CI uses `--reporter=blob` for each phase, overriding the config reporters. Need to either:
  - Add monocart alongside blob: `--reporter=blob,monocart-coverage-reports`
  - Or use env var to conditionally include monocart in the config
- Add Codecov upload step after merge:
  ```yaml
  - name: Upload frontend E2E coverage
    uses: codecov/codecov-action@v4
    with:
      flags: e2e-frontend
      files: web/coverage/e2e/lcov.info
  ```

**Modify: `.github/codecov.yml`**
- Add e2e-frontend flag configuration

### Risks & mitigations

- **Blob reporter + monocart:** When CI uses `--reporter=blob`, this overrides the config file's `reporter` array. Need to verify compatibility or find a workaround.
- **Two-phase merge:** Coverage from DB auth and OIDC phases needs merging. Monocart can write to the same output dir, but need to verify it appends rather than overwrites.
- **Source map resolution:** Production build generates source maps (`webpack.prod.js`). Monocart should resolve TypeScript source paths, but need to verify with the actual webpack config.
- **CI time impact:** V8 coverage collection adds minimal overhead per test. Monocart processing at the end adds ~10-30 seconds.

---

## Phase 3: Nice-to-Haves

### 3A. API Coverage Diff on PRs

**Effort:** ~half day | **Depends on:** Phase 1

Store `api-coverage.json` as a baseline artifact on the default branch. On PR runs, diff against baseline and post a PR comment showing routes that gained/lost coverage. Makes coverage regression visible in code review.

### 3B. Response Code Coverage Matrix Enhancement

**Effort:** ~half day | **Depends on:** Phase 1

Extend Phase 1 to track `(method, route, status_code)` triples. Shows that `DELETE /api/v1/repository/{path}` was tested with `204` but never with `404` or `403`. More actionable than line-level coverage for API testing.

### 3C. Backend Line-Level Coverage via coverage.py

**Status:** NOT recommended

Operationally complex: must patch gunicorn/gevent, flush coverage data from long-running workers, extract `.coverage` files from container. The signal-to-noise ratio is low — unit tests already target 70% line coverage. **Skip unless there's a specific need.**

---

## What we're NOT doing (and why)

- **Backend line-level coverage:** High complexity (gunicorn/gevent/container extraction), low marginal value over unit test coverage
- **Istanbul build instrumentation:** Unnecessary since V8 coverage works without it on Chromium
- **Production/runtime coverage:** Out of scope — this is about CI E2E tests
- **Coverport:** Go-only tool, not applicable

---

## Key files reference

| File | Role |
|------|------|
| `.github/workflows/web-playwright-ci.yaml` | CI workflow (add coverage steps) |
| `.github/scripts/analyze-jaeger-traces.sh` | Existing trace analysis (pattern reference) |
| `.github/scripts/analyze-api-coverage.py` | New script (Phase 1) |
| `.github/codecov.yml` | Codecov config |
| `web/playwright.config.ts` | Playwright config (Phase 2) |
| `web/package.json` | Dependencies (Phase 2) |
| `endpoints/api/discovery.py` | Route enumeration via `app.url_map.iter_rules()` |
| `local-dev/jaeger/jaeger-config.yaml` | Jaeger config (sample_rate: 1.0) |
| `app.py:380-389` | OTEL Flask instrumentation setup |
| `util/metrics/otel.py` | OTEL exporter initialization |
