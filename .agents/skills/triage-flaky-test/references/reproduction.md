# Stage C detail: spec, fixtures, and local reproduction

### C1: map the test name to the spec

The name is the sequence of nested `describe` blocks joined to the title by
` › `. Grep the **last** segment (the test title) under the e2e tree:

```bash
grep -rn "auto theme respects browser color scheme preference" web/playwright/e2e/
```

### C2: read three things, in this order

1. **The spec** — the failing test and, critically, the tests **before** it in
   the same file.
2. **The fixtures it pulls in** (`web/playwright/fixtures.ts`). *This is the
   single highest-yield check.* A worker-scoped fixture shares one
   BrowserContext — and therefore one `localStorage`, one cookie jar — across
   every test that lands on that worker:

   ```bash
   grep -n "scope: 'worker'" web/playwright/fixtures.ts
   ```

   With `fullyParallel: true`, which tests share a worker varies per run, so a
   state leak presents as a flake rather than a failure.
3. **The product code under `web/src`** that the assertion exercises — to decide
   whether the behaviour under test is correct, or the test itself is wrong.

### C3: reproduce locally

Bring up the stack per the rig's local-dev runbook (`make DOCKER=podman
local-dev-up`), then:

**Gotcha 1 — `static/patternfly` may be stale.** Playwright's `webServer` step
builds React and copies it into `static/patternfly`, but
`reuseExistingServer: true` skips that step entirely when something already
answers on :8080, so you can silently test a months-old bundle. Build it first:

```bash
cd web && REACT_QUAY_APP_API_URL=http://localhost:8080 npm run build \
  && rm -rf ../static/patternfly && mkdir -p ../static/patternfly \
  && cp -r dist/* ../static/patternfly/
```

**Gotcha 2 — `--repeat-each` alone will not reproduce an isolation bug.** Under
wide parallelism the shared-context path is rarely exercised; `--workers=1`
forces several tests onto one worker and makes the leak deterministic. Run
both commands — but budget them first: `--repeat-each` multiplies the **whole
file**, and siblings may fail only locally.

```bash
cd web   # paths below are relative to web/, i.e. "${SPEC#web/playwright/}"
npx playwright test e2e/ui/theme-switcher.spec.ts --list | tail -1
# CI-like scheduling — establishes the background rate. Raise toward
# --repeat-each=30 only if --list showed a cheap file.
PLAYWRIGHT_BASE_URL=http://localhost:8080 npx playwright test e2e/ui/theme-switcher.spec.ts --repeat-each=10 --workers=4 --max-failures=5
# forces worker/context reuse — exercises the leak path
PLAYWRIGHT_BASE_URL=http://localhost:8080 npx playwright test e2e/ui/theme-switcher.spec.ts --repeat-each=5 --workers=1
```

Confirm reuse rather than assuming it, from the JSON reporter. Use
`parallelIndex` (the reusable worker **slot**, `0..workers-1`), not
`workerIndex` — a restarted worker process gets a *new* `workerIndex`, so that
count climbs with the repeat count and says nothing about reuse:

```bash
jq '[.. | .parallelIndex? // empty | select(. >= 0)] | unique | length' web/test-results/results.json
```

The `select(. >= 0)` is not optional: a **skipped** test is recorded with
`workerIndex: -1, parallelIndex: -1`, and without the filter that sentinel
counts as an extra slot.

Under `--workers=1` this is `1`. The JSON reporter only writes
`test-results/results.json` when the run **completes** — kill a run early and
there is nothing to read.

State the result as a rate with the exact command, e.g. `0/90` and `5/5`.
**"Did not reproduce in N runs" is a valid outcome.** Never write one up that
did not happen.

### C4: classify

| Class | Evidence that distinguishes it |
|---|---|
| **Test isolation** | Fails only when a sibling test precedes it on the same worker; deterministic under `--workers=1`, absent under wide parallelism; a worker-scoped fixture carries the state. |
| **Test race** | Assertion runs before a signal the test never waits for; fails at varying rates under load; passes with an explicit `waitFor` and no product change. |
| **Product race** | Reproduces with a fresh context and a single worker; the DOM/API state at failure is genuinely wrong, not stale test state. Escalate — do not fix product code as part of this triage. |
| **Infra** | Browser crash, connection refused, worker timeout, pod scheduling; correlates with the job/cluster, not the test order. |
| **Environment** | Fails on one variant/platform/OCP version only, or only against a stale or misconfigured local build (see Gotcha 1). |
| **Insufficient evidence** | Did not reproduce under either command and the CI artifacts were unreachable. Report the rates and the access gap; do not pick a class to fill the box. |
