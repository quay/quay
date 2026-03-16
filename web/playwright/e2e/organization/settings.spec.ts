import {type Page} from '@playwright/test';
import {test, expect} from '../../fixtures';

test.describe('Organization Settings', {tag: ['@organization']}, () => {
  test.describe('General Settings', {tag: ['@feature:USER_METADATA']}, () => {
    test('validates email and saves settings', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('settingstest');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

      // Wait for the form to load
      const emailInput = authenticatedPage.locator('#org-settings-email');
      await expect(emailInput).toBeVisible();

      // Type a bad email
      await emailInput.clear();
      await emailInput.fill('this is not a good e-mail');
      await expect(
        authenticatedPage.getByText('Please enter a valid email address'),
      ).toBeVisible();

      // Leave empty (email field is not required, so no error should appear)
      await emailInput.clear();

      // Check save button is disabled when form is not dirty or invalid
      const saveButton = authenticatedPage.locator('#save-org-settings');
      await expect(saveButton).toBeDisabled();

      // Type a good email and save
      await emailInput.fill('good-email@redhat.com');
      await expect(saveButton).toBeEnabled();
      await saveButton.click();

      // Verify success message
      await expect(
        authenticatedPage.getByText('Successfully updated settings').first(),
      ).toBeVisible();

      // Refresh page and check if email is saved
      await authenticatedPage.reload();
      await expect(emailInput).toHaveValue('good-email@redhat.com');
    });
  });

  test.describe('Billing Information', {tag: ['@feature:BILLING']}, () => {
    test('validates billing email and receipt settings', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('billingtest');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

      // Navigate to billing tab
      await authenticatedPage.getByText('Billing information').click();

      // Wait for billing form to load
      const invoiceEmailInput = authenticatedPage.locator(
        '#billing-settings-invoice-email',
      );
      await expect(invoiceEmailInput).toBeVisible();

      // Type a bad email
      await invoiceEmailInput.clear();
      await invoiceEmailInput.fill('this is not a good e-mail');

      // Check save button is disabled with invalid email
      const saveButton = authenticatedPage.locator('#save-billing-settings');
      await expect(saveButton).toBeDisabled();

      // Clear and type a good email
      await invoiceEmailInput.clear();
      await invoiceEmailInput.fill('invoice-email@redhat.com');

      // Toggle save receipts checkbox
      const checkbox = authenticatedPage.locator('#checkbox');
      await expect(checkbox).not.toBeChecked();
      await checkbox.click();

      // Save
      await expect(saveButton).toBeEnabled();
      await saveButton.click();

      // Verify success message
      await expect(
        authenticatedPage.getByText('Successfully updated settings').first(),
      ).toBeVisible();

      // Refresh page, navigate to billing tab and check if settings are saved
      await authenticatedPage.reload();
      await authenticatedPage.getByText('Billing information').click();
      await expect(invoiceEmailInput).toHaveValue('invoice-email@redhat.com');
      await expect(checkbox).toBeChecked();
    });
  });

  test('CLI token tab not visible for organizations', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('clitest');

    await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

    // Ensure settings page is loaded by checking for the email input
    await expect(
      authenticatedPage.locator('#org-settings-email'),
    ).toBeVisible();

    // Ensure CLI configuration tab is not visible for organizations
    await expect(
      authenticatedPage.getByRole('tab', {name: 'CLI configuration'}),
    ).not.toBeVisible();
  });

  async function gotoSettingsAndWaitForExclusionAPIs(
    page: Page,
    orgName: string,
    action: 'goto' | 'reload' = 'goto',
  ) {
    const waitForAPIs = Promise.all([
      page.waitForResponse(
        (resp) =>
          resp.url().includes(`/organization/${orgName}/mirror`) &&
          resp.request().method() === 'GET',
      ),
      page.waitForResponse(
        (resp) =>
          resp.url().includes(`/organization/${orgName}/proxycache`) &&
          resp.request().method() === 'GET',
      ),
      page.waitForResponse(
        (resp) =>
          resp.url().includes(`/organization/${orgName}/immutabilitypolicy/`) &&
          resp.request().method() === 'GET',
      ),
    ]);

    if (action === 'goto') {
      await page.goto(`/organization/${orgName}?tab=Settings`);
    } else {
      await page.reload();
    }

    await waitForAPIs;
  }

  test.describe(
    'Mutual Exclusion: Org Mirror, Proxy Cache, Immutability',
    {
      tag: [
        '@feature:ORG_MIRROR',
        '@feature:PROXY_CACHE',
        '@feature:IMMUTABLE_TAGS',
      ],
    },
    () => {
      test('hides Proxy Cache and Immutability tabs when org mirror is configured', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization('mexmirr');
        const robot = await api.robot(org.name, 'mirrorbot');

        const syncStartDate = new Date();
        syncStartDate.setMinutes(syncStartDate.getMinutes() + 5);
        await api.raw.createOrgMirrorConfig(org.name, {
          external_registry_type: 'quay',
          external_registry_url: 'https://quay.io',
          external_namespace: 'projectquay',
          robot_username: robot.fullName,
          visibility: 'private',
          sync_interval: 3600,
          sync_start_date: syncStartDate
            .toISOString()
            .replace(/\.\d{3}Z$/, 'Z'),
        });

        await gotoSettingsAndWaitForExclusionAPIs(authenticatedPage, org.name);

        // Organization state tab should be visible
        await expect(
          authenticatedPage.getByTestId('Organization state'),
        ).toBeVisible();

        // Proxy Cache, Immutability, and Auto-Prune tabs should be hidden
        await expect(
          authenticatedPage.getByTestId('Proxy Cache'),
        ).not.toBeAttached();
        await expect(
          authenticatedPage.getByTestId('Immutability Policies'),
        ).not.toBeAttached();
        await expect(
          authenticatedPage.getByTestId('Auto-Prune Policies'),
        ).not.toBeAttached();
      });

      test('hides Organization state and Immutability tabs when proxy cache is configured', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization('mexproxy');

        // Create proxy cache via UI (API requires upstream validation)
        await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
        await authenticatedPage.getByTestId('Proxy Cache').click();
        await authenticatedPage
          .getByTestId('remote-registry-input')
          .fill('docker.io');
        await authenticatedPage.getByTestId('save-proxy-cache-btn').click();
        await expect(
          authenticatedPage
            .getByText('Successfully configured proxy cache')
            .first(),
        ).toBeVisible();

        // Reload to see mutual exclusion take effect
        await gotoSettingsAndWaitForExclusionAPIs(
          authenticatedPage,
          org.name,
          'reload',
        );

        // Proxy Cache tab should be visible
        await expect(
          authenticatedPage.getByTestId('Proxy Cache'),
        ).toBeVisible();

        // Organization state and Immutability tabs should be hidden
        await expect(
          authenticatedPage.getByTestId('Organization state'),
        ).not.toBeAttached();
        await expect(
          authenticatedPage.getByTestId('Immutability Policies'),
        ).not.toBeAttached();
      });

      test('hides Organization state and Proxy Cache tabs when immutability policies exist', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization('meximm');

        await api.orgImmutabilityPolicy(org.name, 'v.*', true);

        await gotoSettingsAndWaitForExclusionAPIs(authenticatedPage, org.name);

        // Immutability Policies tab should be visible
        await expect(
          authenticatedPage.getByTestId('Immutability Policies'),
        ).toBeVisible();

        // Organization state and Proxy Cache tabs should be hidden
        await expect(
          authenticatedPage.getByTestId('Organization state'),
        ).not.toBeAttached();
        await expect(
          authenticatedPage.getByTestId('Proxy Cache'),
        ).not.toBeAttached();
      });

      test('shows all three tabs when none are configured', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization('mexnone');

        await gotoSettingsAndWaitForExclusionAPIs(authenticatedPage, org.name);

        await expect(
          authenticatedPage.getByTestId('Organization state'),
        ).toBeVisible();
        await expect(
          authenticatedPage.getByTestId('Proxy Cache'),
        ).toBeVisible();
        await expect(
          authenticatedPage.getByTestId('Immutability Policies'),
        ).toBeVisible();
        await expect(
          authenticatedPage.getByTestId('Auto-Prune Policies'),
        ).toBeVisible();
      });

      test('tabs reappear after removing conflicting config', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization('mexreapp');

        // Create proxy cache via UI -> org state and immutability should be hidden
        await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
        await authenticatedPage.getByTestId('Proxy Cache').click();
        await authenticatedPage
          .getByTestId('remote-registry-input')
          .fill('docker.io');
        await authenticatedPage.getByTestId('save-proxy-cache-btn').click();
        await expect(
          authenticatedPage
            .getByText('Successfully configured proxy cache')
            .first(),
        ).toBeVisible();

        // Reload to see mutual exclusion take effect
        await gotoSettingsAndWaitForExclusionAPIs(
          authenticatedPage,
          org.name,
          'reload',
        );

        await expect(
          authenticatedPage.getByTestId('Organization state'),
        ).not.toBeAttached();

        // Delete proxy cache via API
        await api.raw.deleteProxyCacheConfig(org.name);

        // Reload and verify tabs reappear
        await gotoSettingsAndWaitForExclusionAPIs(
          authenticatedPage,
          org.name,
          'reload',
        );

        await expect(
          authenticatedPage.getByTestId('Organization state'),
        ).toBeVisible();
        await expect(
          authenticatedPage.getByTestId('Immutability Policies'),
        ).toBeVisible();
        await expect(
          authenticatedPage.getByTestId('Auto-Prune Policies'),
        ).toBeVisible();
      });

      test('hides all three exclusive tabs when immutability fetch errors', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization('mexerr');

        // Intercept the immutability policies endpoint and return a 500 error
        await authenticatedPage.route(
          '**/api/v1/organization/*/immutabilitypolicy/',
          async (route) => {
            await route.fulfill({
              status: 500,
              contentType: 'application/json',
              body: JSON.stringify({
                error_message: 'Internal Server Error',
              }),
            });
          },
        );

        await gotoSettingsAndWaitForExclusionAPIs(authenticatedPage, org.name);

        // General settings should still be visible
        await expect(
          authenticatedPage.getByTestId('General settings'),
        ).toBeVisible();

        // All three mutually-exclusive tabs should be hidden
        await expect(
          authenticatedPage.getByTestId('Organization state'),
        ).not.toBeAttached();
        await expect(
          authenticatedPage.getByTestId('Proxy Cache'),
        ).not.toBeAttached();
        await expect(
          authenticatedPage.getByTestId('Immutability Policies'),
        ).not.toBeAttached();
      });
    },
  );

  test.describe(
    'Repository Settings: Org Mirror Mutual Exclusion',
    {
      tag: ['@repository', '@feature:ORG_MIRROR', '@feature:IMMUTABLE_TAGS'],
    },
    () => {
      test('shows Immutability tab for non-mirrored repos', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization('mexreponorm');
        const repo = await api.repository(org.name, 'normalrepo');

        await authenticatedPage.goto(
          `/repository/${repo.fullName}?tab=settings`,
        );

        // Immutability tab should be visible for a normal repo
        await expect(
          authenticatedPage.getByTestId(
            'settings-tab-repositoryimmutabilitypolicies',
          ),
        ).toBeVisible();

        // No org mirror banner
        await expect(
          authenticatedPage.getByTestId('org-mirror-repo-settings-banner'),
        ).not.toBeAttached();
      });
    },
  );
});
