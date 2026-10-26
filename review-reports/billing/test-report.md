# Billing and organization plans validation

Date: 2026-10-21. PR branch: `feat/billing-plan-checkout-upstream`, based on upstream
`ada8067ee`. Original feature baseline `Plan-info` at `d66650950` is preserved.

## Scope and environment

The two independent agents reviewed the entire original feature diff, including
earlier billing prototypes, rather than only the last commit. Their reports and
fix plans are [PF6 review](pf6-review.md) and
[accessibility review](accessibility-review.md). Both rechecked the remediation.

The upstream diff excludes machine-specific Docker/config/env changes, design
documents, the abandoned OAuth development proxy, the imitation Stripe form,
its branding assets, and its unused saved-card dialog. The real FakeStripe
provider and PF6 simulation page remain. The original branch retains the local
development settings and excluded design work.

Validation used Node 22.23.3, Python 3.12 in Quay and Python 3.14 for an initial
host unit run, PatternFly React Core 6.4.3, Playwright 1.60.0 with installed Chrome,
and axe 4.14.0. Dependencies were installed in an isolated worktree using pnpm
10.20.0; existing runtime dependency versions were retained from upstream.
The original review inspected PF6 6.4.1 before isolated dependencies were installed.

Frontend: `http://localhost:9012`, proxied to the existing Quay backend at
`http://localhost:8082`, with `MOCK_API=false` and FakeStripe. The original server
on port 9010 and its `Plan-info` checkout were preserved. Temporary test accounts
and organizations were created through actual API/UI operations, with no
Playwright response interception or database seeding. The existing organization
regression fixture uses the standard regular test user, without requiring local
administrator credentials.

## Results and exact commands

Commands in this section ran from the PR worktree's `web/` directory unless a
different directory is stated. Node commands used `nvm use 22` first.

### Frontend suite and builds

| Command | Outcome |
| --- | --- |
| `npm test -- --reporter=dot` | Passed: 1,525 tests in 189 files. Includes a return-origin regression for double-slash router prefixes. Existing console warnings remain. |
| `MOCK_API=false REACT_QUAY_APP_API_URL= npm run build` | Passed; two existing webpack bundle-size warnings. |
| `MOCK_API=false npm run build-plugin` | Passed; bundle-size warnings and an existing missing optional frontend CRD notice. Build success does not verify an authenticated console session. |
| `npm run test:e2e:check-required-tags` | Passed. |
| `git diff --check` | Passed. |

The earlier original-branch baseline unit run passed 1,462 tests. After syncing
with current upstream and installing its locked dependency versions, the suite
contains additional upstream tests. Counts above refer to the reviewed PR tree,
not an aggregate of repeated runs.

### Browser suites

```bash
PLAYWRIGHT_CHANNEL=chrome PLAYWRIGHT_SKIP_WEBSERVER=1 \
PLAYWRIGHT_BASE_URL=http://localhost:9012 \
REACT_QUAY_APP_API_URL=http://localhost:8082 PLAYWRIGHT_FAKE_CHECKOUT=true \
  npx playwright test --config playwright/billing-local.config.ts \
  --reporter=list --max-failures=1
```

**Passed: 17; skipped: 2.** Four accessibility tests passed within this run,
including seven scoped axe scans without reported violations. The two skipped
cases require an explicitly unavailable-checkout backend, which the working
FakeStripe environment does not provide. They are not counted as passes.

```bash
PLAYWRIGHT_CHANNEL=chrome PLAYWRIGHT_SKIP_WEBSERVER=1 \
PLAYWRIGHT_BASE_URL=http://localhost:9012 \
REACT_QUAY_APP_API_URL=http://localhost:8082 \
  npx playwright test --config playwright/billing-organization.config.ts \
  --reporter=list --max-failures=1
```

**Passed: 11.** Existing name/email, email lifecycle, organization CRUD,
optional-email, and creation-alert regressions. CRUD now returns from the new
detail page to the list before searching, and the existing alert test selects
the free plan when billing is enabled.

```bash
PLAYWRIGHT_CHANNEL=chrome PLAYWRIGHT_SKIP_WEBSERVER=1 \
PLAYWRIGHT_BASE_URL=http://localhost:9012 \
REACT_QUAY_APP_API_URL=http://localhost:8082 \
  npx playwright test --config playwright/billing-local.config.ts \
  --grep "Create Organization page" --grep-invert "paid checkout failure" \
  --reporter=list --max-failures=1
```

**Passed: 5** with the actual backend `FEATURE_BILLING=false`. The original
configuration was saved, temporarily changed and restarted for this check, then
restored byte-for-byte and restarted. `/config` confirmed billing was restored.

```bash
PLAYWRIGHT_CHANNEL=chrome PLAYWRIGHT_SKIP_WEBSERVER=1 \
PLAYWRIGHT_BASE_URL=http://localhost:9012 \
REACT_QUAY_APP_API_URL=http://localhost:8082 PLAYWRIGHT_FAKE_CHECKOUT=true \
  npx playwright test --config playwright/billing-local.config.ts \
  --grep "Local simulated organization checkout" --reporter=list \
  --output test-results/billing-payment-method
```

**Passed: 2.** Final focused verification includes the payment-method button,
setup-session API, PF6 simulation, returned card summary, and unchanged plan.
This extends the same two cancel/complete cases in the full profile.

```bash
PLAYWRIGHT_CHANNEL=chrome PLAYWRIGHT_BASE_URL=http://localhost:9012 \
  npx playwright test --config playwright/native-billing.config.ts --reporter=list
```

**Skipped: 2; authenticated deployment verification blocked.** No designated
deployed namespace or authenticated deployment storage state was supplied. No
real Stripe payment/session or hosted webhook was exercised by local testing.

### Backend suites

To test current upstream plus the exact changed backend files without changing
the running server, upstream source was archived into
`/tmp/quay-billing-pr-source` inside the existing Quay container and overlaid with
the six PR backend/test files. The existing isolated pytest tools were used.
Commands ran from the original repository directory so Docker Compose used the
running stack configuration.

```bash
docker-compose exec -T -w /tmp/quay-billing-pr-source \
  -e TEST=true -e PYTHONPATH=/tmp/quay-checkout-tests:/tmp/quay-billing-pr-source \
  quay python -m pytest util/test/test_fake_checkout.py \
  data/test/test_fake_billing.py -q --disable-warnings
```

**Passed: 8.** Signed expiry/tampering/origin checks, new-customer free state,
Redis persistence across worker cache reset, plan modification and cancellation.

```bash
docker-compose exec -T -w /tmp/quay-billing-pr-source \
  -e TEST=true -e PYTHONPATH=/tmp/quay-checkout-tests:/tmp/quay-billing-pr-source \
  quay python -m pytest endpoints/api/test/test_security.py \
  -k 'FakeCheckout or all_apis_tested' -q --disable-warnings
```

**Passed: 9; deselected: 1,654.** Authentication/access cases and API security
registry coverage. Remaining security-registry cases were not run.

```bash
docker-compose exec -T -w /tmp/quay-billing-pr-source \
  -e TEST=true -e PYTHONPATH=/tmp/quay-checkout-tests:/tmp/quay-billing-pr-source \
  quay python -m pytest test/test_api_usage.py \
  -k 'billing or plan or card or invoice or marketplace or subscription or Sku or PrivateAllowed' \
  -q --disable-warnings
```

**Passed: 29; deselected: 219.** Existing plan, card, allowance, invoice-setting
and Customer Portal/SKU behavior.

```bash
docker-compose exec -T -w /tmp/quay-billing-pr-source \
  -e TEST=true -e PYTHONPATH=/tmp/quay-checkout-tests:/tmp/quay-billing-pr-source \
  quay python -m pytest test/test_endpoints.py -k 'billing' -q --disable-warnings
```

**Passed: 2; deselected: 78.** Billing-enabled and billing-disabled config cases.

The full backend, registry, and unrelated Playwright suites were **not run**.
The frontend full unit suite and backend/browser suites above cover the changed
feature; this is not a claim that every repository test passed.

### Type checking and hooks

`npx tsc --noEmit` **failed** with 244 diagnostics in the reviewed tree. The same
command against an archive of clean upstream `ada8067ee`, using the same isolated
dependencies, failed with 255. Comparing diagnostics after normalizing line
numbers and dependency symlink prefixes found **zero introduced diagnostics and
11 resolved**. Existing third-party declarations and unrelated source errors
remain; this command is not reported as passed.

Commit-time secret scanning, Python formatting/import/lint checks, ESLint,
lockfile checks, Playwright tags and whitespace hooks are recorded with the
final local commit. No protected local-config hook override is needed for the PR.

The repository's `npm-lockfile-sync` hook incorrectly staged the web lockfile at
the legacy root `package-lock.json` path in this linked worktree. That unrelated
generated change was restored. The web lockfile was synchronized manually with
`npm install --package-lock-only --legacy-peer-deps --ignore-scripts`; its diff
contains only the scanner dependency changes. The final commit skips this one
sync hook (`SKIP=npm-lockfile-sync`), retaining the resolved-URL check, secret scan,
formatters, lint, config guard and other applicable hooks. The hook implementation
was not changed in the PR. Initial ESLint failure was formatter changes, with
zero lint errors and existing warnings; those formatting changes were reviewed.

## Coverage map and remaining checks

| Changed behavior | Evidence | Limit |
| --- | --- | --- |
| Full-page creation, validation, catalog, free selection, duplicate submit, conflicts and cancel | Local profile, organization regressions, billing-disabled run | Unavailable-checkout retry profile remains gated. |
| Paid creation, same-window checkout, cancellation/completion and persistence | Real FakeStripe UI and API suites | Hosted Stripe/authenticated deployment not verified. |
| Existing plan change and authoritative status polling | UI confirmation/PUT, API replay checks, helper units, unconfirmed-return case | Hosted webhook timing requires deployed acceptance. |
| Card setup through button/API and return | Final focused UI check and personal/org API cases | No real card or Stripe payment collected. |
| Invoice preferences and validation | Real save/reload, invalid email descriptions, disabled save and modal focus cycle | Invoice PDF link names source-reviewed; local backend returned no usable invoice list. |
| Customer Portal assignment/removal/quantity | Existing backend SKU tests and frontend hook units; semantic source review | Authenticated entitlement-backed UI/quantity interaction not verified locally. |
| Console billing destinations and return prefix | Shared route registration, prefix/origin units and plugin build | Authenticated console runtime not verified. |
| Field descriptions, radio group, status messages, dialog focus and contrast | Four real-backend accessibility tests; seven scoped axe scans; screenshots | No complete WCAG certification or actual screen-reader speech test. |
| Over-limit usage | Pure tests for normal, exceeded, zero and unlimited allowances; bounded PF6 Progress props | Actual nonzero progress geometry needs an entitlement-backed namespace. |

The new organization form fits within 320 CSS pixels. The inherited header's
action group and off-canvas drawer still widen the document to roughly
640–652 pixels at that viewport; full-page reflow therefore remains deficient.
The test retains DOM evidence and asserts feature geometry rather than silently
claiming the entire application passes. This unrelated shell issue is reported
for follow-up instead of changing global navigation in this feature PR.

Manual VoiceOver/screen-reader speech, real browser zoom/text resizing, forced
colors, focus-obscuration and full deployed flows remain **not run**. Review the
accepted [accessibility screenshots](accessibility-review.md#accepted-screenshots-in-flow-order)
for the exact visual states and limitations.

## Resolved setup and intermediate failures

- Combining `test_endpoints.py` and `test_api_usage.py` in one pytest process
  failed collection because both register the webhooks blueprint. Separate
  processes passed; no unrelated test-framework change was made.
- Temporary Docker host-directory mounts did not expose the isolated pytest
  tools. Copying exact PR source into the existing container resolved this;
  final backend results above use that exact source.
- Standard global setup could not sign in as the unrelated local admin.
  The organization regression profile now provisions/signs in only its regular
  test user through the API, and all 11 selected tests passed.
- Initial accessibility checks exposed inherited whole-page overflow and overly
  exact expectations for PF6's added accessible error-status text. Finite PF6
  error animations are awaited before contrast scans. Final scoped checks pass;
  inherited overflow remains explicitly open.
- Initial upstream merge preparation found a pre-existing private-key fixture
  in upstream secret scanning. The PR was rebuilt directly on current upstream
  with only the feature diff, without modifying/allowlisting the fixture or
  disabling secret scanning.

## Before marking the PR ready

1. Run authenticated Quay.io staging acceptance with a designated namespace:
   verify session/CSRF, checkout and cancellation, webhook-confirmed plan state,
   card setup, invoices and Customer Portal entitlement workflows.
2. Verify billing routes and checkout return prefixes in an authenticated console.
3. Perform supported screen-reader and zoom/forced-colors acceptance, and track
   the inherited small-screen shell overflow separately.
4. Review upstream CI results, address feature regressions, and re-run affected
   checks after any changes. Keep the PR draft while these checks are pending.
