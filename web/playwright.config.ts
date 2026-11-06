import {defineConfig, devices} from '@playwright/test';
import {
  applyChromiumLoopbackBypass,
  proxyOptionFromEnv,
} from './playwright/utils/proxy';

// When Quay is only reachable through a proxy (bare-metal OpenShift CI), route
// the browser and all APIRequestContext traffic through it. Playwright does not
// pick up HTTP(S)_PROXY env vars for live traffic on its own. This module is
// re-evaluated in each worker process, so setting the loopback-bypass env here
// covers every Chromium launch.
applyChromiumLoopbackBypass();
const proxy = proxyOptionFromEnv();

/**
 * Playwright configuration for Quay E2E tests
 * See https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './playwright/e2e',

  // Global setup to create test users before all tests
  globalSetup: require.resolve('./playwright/global-setup'),

  // Maximum time one test can run for
  timeout: 60 * 1000,

  // Run tests in parallel — fixed at 4 for CI so Quay isn't overwhelmed by
  // more workers than it can sustain, regardless of runner CPU count.
  fullyParallel: true,
  workers: process.env.CI ? 4 : undefined,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 1 : 0,

  // Reporter configuration
  reporter: [
    [process.env.CI && !process.env.OPENSHIFT_CI ? 'github' : 'list'],
    ['html', {outputFolder: 'playwright-report'}],
    ['json', {outputFile: 'test-results/results.json'}],
  ],

  // Shared settings for all tests
  use: {
    // Base URL for navigation
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:8080',

    // Accept self-signed certificates (needed for OpenShift CI clusters)
    ignoreHTTPSErrors: true,

    // Route browser + request traffic through the proxy when configured.
    // `proxy` covers the context/page fixtures and APIRequestContext; setting
    // it on `launchOptions` too launches the Chromium process itself with
    // --proxy-server, so manually created `browser.newContext()` contexts
    // inherit the proxy instead of attempting direct (failing) DNS.
    proxy,
    launchOptions: {proxy},

    // Action timeout
    actionTimeout: 30 * 1000,

    // Collect trace on any failed attempt
    trace: 'retain-on-failure',

    // Screenshot only on failure
    screenshot: 'only-on-failure',

    // Video only on failure
    video: 'retain-on-failure',
  },

  // Output directories
  outputDir: 'test-results/',

  // Configure projects for different browsers
  projects: [
    // The health gate is the setup project's teardown, not a dependent
    // project: a teardown runs after its dependents even when they fail.
    {
      name: 'health-gate-setup',
      testMatch: /health\/suite-start\.setup\.ts/,
      teardown: 'health-gate',
    },
    {
      name: 'health-gate',
      testMatch: /health\/v2-health-gate\.teardown\.ts/,
    },
    {
      name: 'chromium',
      use: {...devices['Desktop Chrome'], channel: 'chromium'},
      dependencies: ['health-gate-setup'],
    },
  ],

  // Configure web server for local development
  // Note: In OpenShift CI (Prow), services are already running on the cluster.
  // API-only tests (test:api) skip this since they only need Quay, not the frontend.
  webServer:
    process.env.OPENSHIFT_CI || process.env.PLAYWRIGHT_SKIP_WEBSERVER
      ? undefined
      : {
          command:
            'REACT_QUAY_APP_API_URL=http://localhost:8080 npm run build && ' +
            'rm -rf ../static/patternfly && mkdir -p ../static/patternfly && cp -r dist/* ../static/patternfly/ && ' +
            'echo "React deployed to static/patternfly/" && tail -f /dev/null',
          url: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:8080',
          reuseExistingServer: true,
          timeout: 120 * 1000,
        },
});
