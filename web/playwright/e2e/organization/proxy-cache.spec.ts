import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

test.describe(
  'Organization Proxy Cache',
  {tag: ['@organization', '@feature:PROXY_CACHE']},
  () => {
    test('proxy cache lifecycle: create anonymous config, verify, and delete', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: Create organization
      const org = await api.organization('proxycache');

      // Navigate to org settings
      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByText('Proxy Cache').click();

      // Create anonymous proxy cache config
      await authenticatedPage
        .getByTestId('remote-registry-input')
        .fill('docker.io');
      await authenticatedPage.getByTestId('save-proxy-cache-btn').click();

      // Verify success alert (use first() to handle potential duplicate alerts)
      await expect(
        authenticatedPage
          .getByText('Successfully configured proxy cache')
          .first(),
      ).toBeVisible();

      // Delete the config
      await authenticatedPage.getByTestId('delete-proxy-cache-btn').click();

      // Verify delete success
      await expect(
        authenticatedPage
          .getByText('Successfully deleted proxy cache configuration')
          .first(),
      ).toBeVisible();

      // Verify via API that proxy cache is deleted (API returns empty object when no config)
      const proxyConfig = await api.raw.getProxyCacheConfig(org.name);
      expect(proxyConfig?.upstream_registry).toBeFalsy();
    });

    test('proxy cache form validation: invalid credentials show error', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: Create organization
      const org = await api.organization('proxycreds');

      // Navigate to org settings
      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByText('Proxy Cache').click();

      // Fill form with invalid credentials
      await authenticatedPage
        .getByTestId('remote-registry-input')
        .fill('docker.io');
      await authenticatedPage
        .getByTestId('remote-registry-username')
        .fill('invaliduser');
      await authenticatedPage
        .getByTestId('remote-registry-password')
        .fill('invalidpass');
      await authenticatedPage.getByTestId('remote-registry-expiration').clear();
      await authenticatedPage
        .getByTestId('remote-registry-expiration')
        .fill('76400');

      await authenticatedPage.getByTestId('save-proxy-cache-btn').click();

      // Verify validation error is shown for invalid credentials
      await expect(
        authenticatedPage.getByText('Failed login to remote registry').first(),
      ).toBeVisible();

      // Save button should still be enabled (config not saved)
      await expect(
        authenticatedPage.getByTestId('save-proxy-cache-btn'),
      ).toBeEnabled();

      // Delete button should be disabled (no config exists)
      await expect(
        authenticatedPage.getByTestId('delete-proxy-cache-btn'),
      ).toBeDisabled();
    });

    test('proxy cache form is functional when FEATURE_IMMUTABLE_TAGS is disabled (PROJQUAY-11119)', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('proxynoimm');

      // Override config to disable IMMUTABLE_TAGS (the bug scenario)
      await authenticatedPage.route('**/config', async (route) => {
        const response = await route.fetch();
        const body = await response.json();
        body.features.IMMUTABLE_TAGS = false;
        body.features.PROXY_CACHE = true;
        await route.fulfill({response, body: JSON.stringify(body)});
      });

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByText('Proxy Cache').click();

      // The immutability error alert should NOT be visible
      await expect(
        authenticatedPage.getByTestId('immutability-error-alert'),
      ).not.toBeAttached();

      // Save button should be enabled (not blocked by immutability check)
      await authenticatedPage
        .getByTestId('remote-registry-input')
        .fill('docker.io');
      await expect(
        authenticatedPage.getByTestId('save-proxy-cache-btn'),
      ).toBeEnabled();
    });

    test('proxy cache form is functional when FEATURE_ORG_MIRROR is disabled (PROJQUAY-11478)', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('proxynomirr');

      // Override config to disable ORG_MIRROR (the bug scenario)
      await authenticatedPage.route('**/config', async (route) => {
        const response = await route.fetch();
        const body = await response.json();
        body.features.ORG_MIRROR = false;
        body.features.PROXY_CACHE = true;
        await route.fulfill({response, body: JSON.stringify(body)});
      });

      // Intercept the org mirror endpoint to return 405 (simulates unregistered route)
      await authenticatedPage.route(
        `**/api/v1/organization/${org.name}/mirror`,
        async (route) => {
          await route.fulfill({
            status: 405,
            contentType: 'application/json',
            body: JSON.stringify({error_message: 'Method Not Allowed'}),
          });
        },
      );

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByText('Proxy Cache').click();

      // The org mirror error alert should NOT be visible
      await expect(
        authenticatedPage.getByTestId('org-mirror-error-alert'),
      ).not.toBeAttached();

      // Save button should be enabled (not blocked by org mirror check)
      await authenticatedPage
        .getByTestId('remote-registry-input')
        .fill('docker.io');
      await expect(
        authenticatedPage.getByTestId('save-proxy-cache-btn'),
      ).toBeEnabled();
    });

    test('proxy cache rejects private IP as upstream registry (PROJQUAY-11180)', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('proxyssrf');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByText('Proxy Cache').click();

      await authenticatedPage
        .getByTestId('remote-registry-input')
        .fill('10.0.0.1');
      await authenticatedPage.getByTestId('save-proxy-cache-btn').click();

      await expect(
        authenticatedPage
          .getByText('The provided registry URL is not allowed')
          .first(),
      ).toBeVisible();

      await expect(
        authenticatedPage.getByTestId('save-proxy-cache-btn'),
      ).toBeEnabled();

      await expect(
        authenticatedPage.getByTestId('delete-proxy-cache-btn'),
      ).toBeDisabled();
    });

    test('proxy cache rejects cloud metadata endpoint as upstream registry (PROJQUAY-11180)', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('proxymeta');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByText('Proxy Cache').click();

      await authenticatedPage
        .getByTestId('remote-registry-input')
        .fill('169.254.169.254');
      await authenticatedPage.getByTestId('save-proxy-cache-btn').click();

      await expect(
        authenticatedPage
          .getByText('The provided registry URL is not allowed')
          .first(),
      ).toBeVisible();

      await expect(
        authenticatedPage.getByTestId('save-proxy-cache-btn'),
      ).toBeEnabled();

      await expect(
        authenticatedPage.getByTestId('delete-proxy-cache-btn'),
      ).toBeDisabled();
    });

    test('proxy cache tab not visible for user namespaces', async ({
      authenticatedPage,
    }) => {
      // Navigate to user settings (the authenticated test user is a user namespace, not org)
      await authenticatedPage.goto(
        `/organization/${TEST_USERS.user.username}?tab=Settings`,
      );

      // Proxy Cache tab should not exist for user namespaces
      await expect(
        authenticatedPage.getByText('Proxy Cache'),
      ).not.toBeVisible();
    });
  },
);

/**
 * Air-gapped proxy-route acceptance (real Quay deployment with HTTP_PROXY and SSRF allowlist).
 * Set PLAYWRIGHT_PROXY_SSRF_E2E=1 and PLAYWRIGHT_PROXY_CACHE_UPSTREAM to the allowlisted hostname.
 */
const proxySsrfE2E = process.env.PLAYWRIGHT_PROXY_SSRF_E2E === '1';

test.describe(
  'Proxy cache proxy-route SSRF deployment',
  {tag: ['@organization', '@feature:PROXY_CACHE', '@PROJQUAY-12813']},
  () => {
    test.skip(
      !proxySsrfE2E,
      'requires proxy+allowlist Quay deployment (PLAYWRIGHT_PROXY_SSRF_E2E=1)',
    );

    test('allowlisted unresolved upstream saves proxy cache config', async ({
      authenticatedPage,
      api,
    }) => {
      const upstream = process.env.PLAYWRIGHT_PROXY_CACHE_UPSTREAM;
      test.skip(!upstream, 'PLAYWRIGHT_PROXY_CACHE_UPSTREAM not set');

      const org = await api.organization('proxycachessrf');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByText('Proxy Cache').click();
      await authenticatedPage
        .getByTestId('remote-registry-input')
        .fill(upstream);
      await authenticatedPage.getByTestId('save-proxy-cache-btn').click();

      await expect(
        authenticatedPage
          .getByText('Successfully configured proxy cache')
          .first(),
      ).toBeVisible();

      const proxyConfig = await api.raw.getProxyCacheConfig(org.name);
      expect(proxyConfig?.upstream_registry).toBe(upstream);
    });

    test('non-allowlisted unresolved upstream is rejected', async ({
      authenticatedPage,
      api,
    }) => {
      const upstream =
        process.env.PLAYWRIGHT_PROXY_CACHE_NON_ALLOWLISTED_UPSTREAM ??
        'non-allowlisted-isolated.example.com';

      const org = await api.organization('proxycachessrfneg');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByText('Proxy Cache').click();
      await authenticatedPage
        .getByTestId('remote-registry-input')
        .fill(upstream);
      await authenticatedPage.getByTestId('save-proxy-cache-btn').click();

      await expect(
        authenticatedPage.getByText(/not allowed|failed/i).first(),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('save-proxy-cache-btn'),
      ).toBeEnabled();

      const proxyConfig = await api.raw.getProxyCacheConfig(org.name);
      expect(proxyConfig?.upstream_registry).toBeFalsy();
    });

    test('NO_PROXY upstream is rejected in DNS-isolated deployment', async ({
      authenticatedPage,
      api,
    }) => {
      const upstream = process.env.PLAYWRIGHT_PROXY_NO_PROXY_UPSTREAM;
      test.skip(!upstream, 'PLAYWRIGHT_PROXY_NO_PROXY_UPSTREAM not set');

      const org = await api.organization('proxycachenoproxy');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByText('Proxy Cache').click();
      await authenticatedPage
        .getByTestId('remote-registry-input')
        .fill(upstream);
      await authenticatedPage.getByTestId('save-proxy-cache-btn').click();

      await expect(
        authenticatedPage.getByText(/not allowed|failed/i).first(),
      ).toBeVisible();

      const proxyConfig = await api.raw.getProxyCacheConfig(org.name);
      expect(proxyConfig?.upstream_registry).toBeFalsy();
    });
  },
);
