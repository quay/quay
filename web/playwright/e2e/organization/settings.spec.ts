import {type Page} from '@playwright/test';
import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

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
    'Organization state tab with IMMUTABLE_TAGS disabled',
    {tag: ['@feature:ORG_MIRROR']},
    () => {
      test('shows Organization state tab when FEATURE_IMMUTABLE_TAGS is disabled (PROJQUAY-11028)', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization('mexnoimmtag');

        // Override config to disable IMMUTABLE_TAGS
        await authenticatedPage.route('**/config', async (route) => {
          const response = await route.fetch();
          const body = await response.json();
          body.features.IMMUTABLE_TAGS = false;
          body.features.ORG_MIRROR = true;
          await route.fulfill({response, body: JSON.stringify(body)});
        });

        await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

        // Wait for settings to load
        await expect(
          authenticatedPage.locator('#org-settings-email'),
        ).toBeVisible();

        // Organization state tab should be visible even without IMMUTABLE_TAGS
        await expect(
          authenticatedPage.getByTestId('Organization state'),
        ).toBeVisible();
      });
    },
  );

  test.describe(
    'Organization state tab with PROXY_CACHE disabled',
    {tag: ['@feature:ORG_MIRROR']},
    () => {
      test('shows Organization state tab when FEATURE_PROXY_CACHE is disabled (PROJQUAY-11080)', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization('mexnoproxy');

        // Override config to disable PROXY_CACHE
        await authenticatedPage.route('**/config', async (route) => {
          const response = await route.fetch();
          const body = await response.json();
          body.features.PROXY_CACHE = false;
          body.features.ORG_MIRROR = true;
          await route.fulfill({response, body: JSON.stringify(body)});
        });

        await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

        // Wait for settings to load
        await expect(
          authenticatedPage.locator('#org-settings-email'),
        ).toBeVisible();

        // Organization state tab should be visible even without PROXY_CACHE
        await expect(
          authenticatedPage.getByTestId('Organization state'),
        ).toBeVisible();
      });
    },
  );

  test.describe(
    'Mutual exclusion tabs with ORG_MIRROR disabled',
    {tag: ['@feature:PROXY_CACHE', '@feature:IMMUTABLE_TAGS']},
    () => {
      test('shows Proxy Cache and Immutability tabs when FEATURE_ORG_MIRROR is disabled', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization('mexnomirror');

        // Override config to disable ORG_MIRROR
        await authenticatedPage.route('**/config', async (route) => {
          const response = await route.fetch();
          const body = await response.json();
          body.features.ORG_MIRROR = false;
          body.features.PROXY_CACHE = true;
          body.features.IMMUTABLE_TAGS = true;
          await route.fulfill({response, body: JSON.stringify(body)});
        });

        await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

        // Wait for settings to load
        await expect(
          authenticatedPage.locator('#org-settings-email'),
        ).toBeVisible();

        // Proxy Cache and Immutability tabs should be visible
        await expect(
          authenticatedPage.getByTestId('Proxy Cache'),
        ).toBeVisible();
        await expect(
          authenticatedPage.getByTestId('Immutability Policies'),
        ).toBeVisible();

        // Organization state tab should not be visible (feature disabled)
        await expect(
          authenticatedPage.getByTestId('Organization state'),
        ).not.toBeAttached();
      });
    },
  );

  test.describe(
    'User Namespace Settings: Auto-Prune Policies tab (PROJQUAY-11158)',
    {tag: ['@feature:AUTO_PRUNE', '@user']},
    () => {
      const username = TEST_USERS.user.username;

      // Helper: navigate to user namespace settings with a config override and
      // wait for the General Settings form to confirm the page is fully rendered.
      async function gotoUserSettingsWithConfig(
        page: Page,
        featureOverrides: Record<string, boolean>,
      ) {
        await page.route('**/config', async (route) => {
          const response = await route.fetch();
          const body = await response.json();
          Object.assign(body.features, featureOverrides);
          await route.fulfill({response, body: JSON.stringify(body)});
        });

        await page.goto(`/user/${username}?tab=Settings`);

        // #form-name is always present in user namespace General Settings
        // and appears only after quayConfig is resolved, making it a reliable
        // signal that the tab list has been computed.
        await expect(page.locator('#form-name')).toBeVisible();
      }

      test('shows Auto-Prune Policies tab when PROXY_CACHE is enabled (PROJQUAY-11158)', async ({
        authenticatedPage,
      }) => {
        // Regression scenario: React Query v4 keeps disabled queries in
        // isLoading=true. useFetchProxyCacheConfig is disabled for user orgs
        // (enabled = PROXY_CACHE && !isUserOrg). When PROXY_CACHE=true the
        // hook is disabled but isLoading stays true, making proxyCacheResolved
        // false and blocking mutualExclusionLoaded -> Auto-Prune hidden.
        await gotoUserSettingsWithConfig(authenticatedPage, {
          AUTO_PRUNE: true,
          PROXY_CACHE: true,
          IMMUTABLE_TAGS: false, // keeps immutabilityResolved=true immediately
        });

        // Auto-Prune Policies tab must exist in the sidebar for user namespace
        const autoPruneTab = authenticatedPage.getByTestId(
          'Auto-Prune Policies',
        );
        await expect(autoPruneTab).toBeVisible();

        // Click the tab and verify the Auto-Prune content actually renders.
        // This confirms the tab is not just present but fully navigable, and
        // that the AutoPruning component mounts correctly for user namespaces.
        await autoPruneTab.click();
        await expect(
          authenticatedPage.getByRole('heading', {
            name: 'Auto-Pruning Policies',
            level: 2,
          }),
        ).toBeVisible();

        // Proxy Cache is an org-only feature; must never appear for user namespace
        await expect(
          authenticatedPage.getByTestId('Proxy Cache'),
        ).not.toBeAttached();
      });

      test('shows Auto-Prune Policies tab when ORG_MIRROR is enabled (PROJQUAY-11158)', async ({
        authenticatedPage,
      }) => {
        // Same bug path via useOrgMirrorExists being disabled for user orgs
        // while ORG_MIRROR feature flag is true.
        await gotoUserSettingsWithConfig(authenticatedPage, {
          AUTO_PRUNE: true,
          ORG_MIRROR: true,
          IMMUTABLE_TAGS: false,
        });

        await expect(
          authenticatedPage.getByTestId('Auto-Prune Policies'),
        ).toBeVisible();

        // Organization state is an org-only feature; must never appear for user namespace
        await expect(
          authenticatedPage.getByTestId('Organization state'),
        ).not.toBeAttached();
      });

      test('shows Auto-Prune Policies tab when both PROXY_CACHE and ORG_MIRROR are enabled (PROJQUAY-11158)', async ({
        authenticatedPage,
      }) => {
        // Worst-case scenario: both exclusive features enabled simultaneously.
        // Both disabled hooks would each independently block mutualExclusionLoaded
        // without the fix.
        await gotoUserSettingsWithConfig(authenticatedPage, {
          AUTO_PRUNE: true,
          PROXY_CACHE: true,
          ORG_MIRROR: true,
          IMMUTABLE_TAGS: false,
        });

        await expect(
          authenticatedPage.getByTestId('Auto-Prune Policies'),
        ).toBeVisible();

        await expect(
          authenticatedPage.getByTestId('Proxy Cache'),
        ).not.toBeAttached();
        await expect(
          authenticatedPage.getByTestId('Organization state'),
        ).not.toBeAttached();
      });

      test('CLI configuration tab is visible and org-only tabs are absent in user namespace', async ({
        authenticatedPage,
      }) => {
        // Confirms the tab set for user namespaces is correct: CLI config
        // is user-only, Proxy Cache / Org State are org-only.
        await gotoUserSettingsWithConfig(authenticatedPage, {
          AUTO_PRUNE: true,
          PROXY_CACHE: true,
          ORG_MIRROR: true,
          IMMUTABLE_TAGS: false,
        });

        // CLI configuration is user-namespace only
        await expect(
          authenticatedPage.getByTestId('CLI configuration'),
        ).toBeVisible();

        // Org-only tabs must not render in user namespace
        await expect(
          authenticatedPage.getByTestId('Proxy Cache'),
        ).not.toBeAttached();
        await expect(
          authenticatedPage.getByTestId('Organization state'),
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
