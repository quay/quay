import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {tryPushImage} from '../../utils/container';

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

    test(
      'push to proxy cache organization is blocked',
      {tag: ['@container', '@PROJQUAY-9516']},
      async ({api}) => {
        // Create organization and configure as proxy cache
        const org = await api.organization('pushblock');
        await api.raw.createProxyCacheConfig(org.name, {
          upstream_registry: 'docker.io',
        });

        // Attempt to push an image to the proxy cache org
        // This should fail because proxy cache orgs are read-only
        const result = await tryPushImage(
          org.name,
          'testpush',
          'latest',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );

        // Push should fail
        expect(result.success).toBe(false);

        // Error should indicate access was denied
        // The registry returns "denied" or "unauthorized" when push permissions are blocked
        expect(result.error?.toLowerCase()).toMatch(
          /denied|unauthorized|access/,
        );
      },
    );

    test(
      'repository creation via push is blocked for proxy cache organizations',
      {tag: ['@container', '@PROJQUAY-9516']},
      async ({api}) => {
        // Create organization and configure as proxy cache
        const org = await api.organization('repocreateblock');
        await api.raw.createProxyCacheConfig(org.name, {
          upstream_registry: 'docker.io',
        });

        // Attempt to push to a non-existent repo (would create it normally)
        const result = await tryPushImage(
          org.name,
          'newrepo',
          'v1.0.0',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );

        // Push should fail - can't create repos in proxy cache orgs
        expect(result.success).toBe(false);
        expect(result.error?.toLowerCase()).toMatch(
          /denied|unauthorized|access/,
        );
      },
    );
  },
);
