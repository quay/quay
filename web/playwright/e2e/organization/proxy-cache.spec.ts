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
