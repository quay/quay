# Quay UI

UI for Quay based on React and Patternfly framework

## Installation

It is assumed that you have a Quay instance running that you can point the UI to.
Run the following commands to get started

```bash
git clone https://github.com/quay/quay-ui.git
cd quay-ui
npm install
```

## Development

Start the dev server by running

```bash
npm start
```

Runs the app in the development mode.\
Open [http://localhost:9000](http://localhost:9000) to view it in the browser.

The page will reload if you make edits.\
You will also see any lint errors in the console.

By default the UI connects to the quay backend for API. If you don't have
a backend or want to develop without a backend you can set the environment
variable `MOCK_API=true` before running `npm start`.

In order for you to use this with a Quay backend, you need to configure CORS on the Quay side.
Add the following to your `config.yaml` in Quay

```yaml
CORS_ORIGIN: "http://localhost:9000"
```

If you are using `docker-compose` for local development, you can add this to `local-dev/stack/config.yaml`
in the Quay repo.

## Testing

```bash
npm test
```

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### E2E Tests

E2E tests use [Playwright](https://playwright.dev/). See `web/playwright/` for tests and configuration.

To run tests locally:
- Start the application with `pnpm start`
- Run the tests with `pnpm run test:e2e`

#### Failure artifacts

On a failed test attempt, in addition to the Playwright trace/screenshot/video,
the test report gets one more attachment: `server-spans.json` (backend spans
for the test from Jaeger). Every test also carries a `trace-id` annotation
(visible in the HTML report and the JSON report's test annotations) — look it
up directly in Jaeger's trace search.

Span collection degrades gracefully instead of failing the test: if
`JAEGER_QUERY_URL` is unset or unreachable, the trace is empty, or the reply
is malformed, the reason is recorded as a line in `not-collected.txt` instead
of the span attachment. This never fails a test and adds at most ~14s, only
on failure.

Env var (optional):
- `JAEGER_QUERY_URL` — must be set for Jaeger span collection; unset skips it
  gracefully

No redaction is applied: CI stacks are throwaway and torn down before the
report is published.

## Building for Production

```bash
npm run build
```

Builds the app for production to the `dist` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.
See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

## Organization plans and billing

With `FEATURE_BILLING` enabled, Plan information in organization settings shows
the plan, usage, payment method, invoices, and Customer Portal subscriptions.
The plans, invoices, and subscriptions pages are available in both UI shells.

Organization creation opens `/organizations/new` in the current page. Free
plans create the organization immediately. Paid plans create it once, then open
the checkout URL returned by its plan API in the same window. A failed checkout
retains the organization and offers Retry checkout and Go to organization.

Deployed Quay.io uses its existing authenticated session and CSRF handling.
`POST /api/v1/organization/{name}/plan` (or `/api/v1/user/plan`) starts checkout
for a new paid subscription; `PUT` updates an existing subscription. The card
endpoint starts payment-method setup. Return URLs preserve the current origin
and console router prefix. The UI refreshes the subscription and verifies its
plan and status before confirming a change. Stripe keys and card details remain
outside the frontend.

### Local FakeStripe checkout

Set `FEATURE_BILLING: true` and `BILLING_TYPE: FakeStripe` in your local backend
configuration. Signed, expiring sessions restrict completion to the original
administrator and namespace. Complete simulated checkout saves a sample Visa
ending in 4242 and activates the local plan; Cancel leaves it unchanged. No
payment or card details are collected. State persists in the configured Redis
service. Fake checkout endpoints exist only for the FakeStripe provider.

Run the frontend against the backend with the mock API disabled. The proxy
defaults to `http://localhost:8080`; override it for another backend port:

```bash
MOCK_API=false REACT_QUAY_APP_API_URL= QUAY_PROXY_TARGET=http://localhost:8082 \
  npm start -- --port 9010 --host 127.0.0.1 --no-open
```

The empty `REACT_QUAY_APP_API_URL` makes requests use the webpack proxy. The
existing `MOCK_API=true` fixtures also use the PF6 simulation page, without an
imitation card-entry form. Production builds should use `MOCK_API=false`.

### Billing validation

```bash
npm test
MOCK_API=false npm run build
MOCK_API=false npm run build-plugin

PLAYWRIGHT_CHANNEL=chrome PLAYWRIGHT_SKIP_WEBSERVER=1 \
PLAYWRIGHT_BASE_URL=http://localhost:9010 \
REACT_QUAY_APP_API_URL=http://localhost:8082 PLAYWRIGHT_FAKE_CHECKOUT=true \
  npx playwright test --config playwright/billing-local.config.ts
```

The local Playwright profile provisions temporary accounts through the real API
and checks creation, subscription changes, checkout cancellation/completion,
authorization, keyboard use, dialog focus, reflow, and axe accessibility scans.
It requires Database authentication without email verification and cleans up
its temporary accounts and organizations.

`playwright/native-billing.config.ts` accepts `QUAY_BILLING_STORAGE_STATE` and
`QUAY_BILLING_NAMESPACE` for an authenticated deployed session. Its checkout
write test additionally requires `QUAY_BILLING_CREATE_CHECKOUT=true` and
`QUAY_BILLING_CHECKOUT_PLAN`. These deployment tests can create real Stripe
sessions. Local FakeStripe tests do not verify hosted webhooks or authenticated
console integration. Review reports and exact validation results are in
`../review-reports/billing/`.
