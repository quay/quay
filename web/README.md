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
CORS_ORIGIN: 'http://localhost:9000'
```

If you are using `docker-compose` for local development, you can add this to `local-dev/stack/config.yaml`
in the Quay repo.

## Billing when deployed within Quay.io

The deployed React UI uses the signed-in Quay.io session and CSRF token to call
same-origin billing endpoints. Build the native UI with:

```bash
MOCK_API=false QUAY_HOSTED=false REACT_QUAY_APP_API_URL= npm run build
```

Deploy the built assets with the Quay.io backend and enable or select the React
UI for the account under test. The backend owns Stripe
credentials, plan prices, and Checkout session creation. The plan catalog comes
from `/api/v1/plans/`. New paid subscriptions POST to `/api/v1/user/plan` or
`/api/v1/organization/<name>/plan`, and the browser opens the returned Stripe
Checkout URL. Existing subscriptions use PUT on the same endpoint after a
confirmation. Return URLs use the runtime origin, so they point back to Quay.io
after deployment. The billing page checks fresh subscription data before showing
success, including after an existing-plan update.

Organization creation is a full-page flow at `/organizations/new`, opened by
both organization-list creation buttons. With billing enabled, select an
organization plan before submitting. Free plans create the organization and
open its page. Paid plans create the organization first, then POST its selected
plan to the organization Checkout endpoint and navigate the current browser
window to Stripe. Both return URLs point to the new organization's billing page.
If Checkout cannot start, the creation page keeps the created organization and
offers payment retry or navigation to the organization. Retry checks for an
existing subscription and does not repeat organization creation. With billing
disabled, the page requires only the existing organization fields.

The local backend's `BILLING_TYPE: FakeStripe` mode opens a clearly labeled
simulated checkout at `/fake-checkout`. Choose **Complete simulated checkout**
to activate the selected local plan and a sample Visa ending in 4242, or
**Cancel** to return without subscribing. No real payment details are needed or
collected. Fake customer state is shared through the configured user-events
Redis service so plan reads, updates, and cancellation remain consistent across
web workers. The signed links expire after one hour and require their original
signed-in administrator and matching localhost return URLs. This mode does not
create real Stripe Checkout sessions. The OAuth proxy described below is a
separate development profile; native deployment uses the existing session.

With the frontend on port 9010 and local backend on 8082, run the isolated
session tests without the shared admin account:

```bash
PLAYWRIGHT_CHANNEL=chrome PLAYWRIGHT_BASE_URL=http://localhost:9010 \
REACT_QUAY_APP_API_URL=http://localhost:8082 \
PLAYWRIGHT_FAKE_CHECKOUT=true \
  npx playwright test --config playwright/billing-local.config.ts
```

These tests cover plan selection and organization creation, and create and clean
up temporary accounts through the API. The fake-checkout option additionally
tests simulated completion, cancellation, authorization, and persisted plan
changes. Use `PLAYWRIGHT_BILLING_EXPECT_CHECKOUT_ERROR=true` only when explicitly
testing a backend where checkout is unavailable.

To validate a deployed native UI, provide a Playwright session state file for a
designated account and the deployment's origin. Keep session state in the ignored
`.playwright/` directory. These checks use real API requests and no mocks:

```bash
export PLAYWRIGHT_BASE_URL=https://stage.quay.io
export QUAY_BILLING_NAMESPACE=your_namespace
export QUAY_BILLING_STORAGE_STATE=.playwright/billing-session.json
npx playwright test --config playwright/native-billing.config.ts
```

The default check only reads billing data and reviews an existing-plan change
without submitting it. To also create a real Checkout session for a namespace
without a subscription, explicitly select a paid plan and opt in:

```bash
QUAY_BILLING_CREATE_CHECKOUT=true QUAY_BILLING_CHECKOUT_PLAN=bus-micro-2018 \
  npx playwright test --config playwright/native-billing.config.ts
```

This opens Checkout and exercises the cancellation return without submitting the
payment form. It verifies the native session and CSRF request, the selected plan,
and return URL origin. Session state, screenshots, traces, and videos are not
written by this deployed-account test configuration.

## Local UI with hosted Quay.io billing

Run `npm run start:hosted` to serve the local UI at **https://localhost:9010**
with hot reload and a same-origin proxy to `https://quay.io`. This profile ignores
`.env.development`, disables the mock API and sample invoice assets, and needs no
local Quay backend or Stripe API key. Quay.io creates the Stripe Checkout sessions.

Create an OAuth application/token in Quay.io under Organization → Applications →
Generate Token. Grant `user:read`, plus `user:admin` for personal billing and/or
`org:admin` for organization billing; the token's user must administer the organization.
See the [Quay OAuth documentation](https://docs.quay.io/api/).
Configure the token only in the terminal running the development server. For zsh:

```zsh
cd web
read -rs 'QUAY_OAUTH_TOKEN?Quay OAuth token: '
export QUAY_OAUTH_TOKEN
export QUAY_HOSTED_NAMESPACE=your_namespace
npm run check:hosted
npm run start:hosted
```

The token stays in the Node process. It is added to upstream API requests only;
it is never a React environment variable. Do not paste tokens into source files,
chat, URLs, or command arguments. The proxy binds to loopback, validates local
origins and XHR headers, verifies upstream TLS, and strips browser credentials and
upstream session cookies. Signing in to quay.io in another tab does not authenticate
this profile. To switch accounts, stop the server, replace the token, restart, and
reload the local page. An expired/revoked token requires the same process.

Webpack supplies a development HTTPS certificate by default. For a trusted local
certificate, set `QUAY_DEV_TLS_CERT` and `QUAY_DEV_TLS_KEY` to certificate/key files
outside the repository before starting. Both must cover `localhost`. Set `PORT`
to change 9010; use that same origin in checkout and Playwright.

Open `/organization/your_namespace?tab=Settings&settingsTab=billinginformation`.
Validate read access first with `npm run check:hosted` and, with the server running,
`PLAYWRIGHT_CHANNEL=chrome npm run test:hosted`. These checks never submit payments
or change subscriptions. Hosted browser checks do not record account traces or screenshots.

The proxy starts **read-only**. To intentionally enable real billing changes for
the designated account, restart it with:

```zsh
QUAY_BILLING_WRITES=true npm run start:hosted
```

Only plan POST/PUT and card-setup POST requests are enabled by this switch. Other
writes, including invoice settings and Customer Portal subscription assignment,
remain blocked in this development profile. Billing writes act on the real Quay.io
account and can incur charges. Automated checks do not complete live Checkout.

New paid subscriptions use POST `/api/v1/user/plan` or
`/api/v1/organization/<name>/plan` and navigate to the returned Stripe URL.
Existing subscription changes use PUT on the same route after confirmation;
opening a new subscription Checkout for an existing subscriber could duplicate it.
Payment changes use POST on the corresponding `/card` route, which requires an
existing subscription. Success/cancel URLs return to this local origin. After a
return, the UI refreshes authoritative billing data for up to ten seconds while
the hosted Quay webhook completes. A redirect alone does not confirm a plan change.

The hosted deployment's endpoint availability, OAuth permissions, and acceptance
of local return URLs must be verified with the designated account; repository
source alone does not establish compatibility. The mock-only bulk invoice ZIP is
disabled outside mock mode. Individual receipts open on quay.io, whose receipt
route requires a browser session; sign in there to download them. The development
proxy's OAuth token does not establish that browser session.
To return to the prototype, stop the hosted server and
run `MOCK_API=true npm start -- --port 9010 --host 127.0.0.1 --no-open` (HTTP).

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
