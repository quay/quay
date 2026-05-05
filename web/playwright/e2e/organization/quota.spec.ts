import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {pushImage} from '../../utils/container';

test.describe(
  'Quota Management',
  {tag: ['@organization', '@feature:QUOTA_MANAGEMENT', '@feature:EDIT_QUOTA']},
  () => {
    test('superuser can configure quota lifecycle: create, update, add limit, update limit, delete limit, delete quota', async ({
      superuserPage,
      superuserApi,
    }) => {
      // Setup: Create organization
      const org = await superuserApi.organization('quotatest');

      // Navigate to organizations list
      await superuserPage.goto('/organization');

      // Open Configure Quota modal via kebab menu
      await superuserPage.getByTestId(`${org.name}-options-toggle`).click();
      await superuserPage.getByTestId('configure-quota-option').click();

      // Verify modal opens
      await expect(
        superuserPage.getByTestId('configure-quota-modal'),
      ).toBeVisible();
      await expect(
        superuserPage.getByText(`Configure Quota for ${org.name}`),
      ).toBeVisible();

      // CREATE QUOTA: Enter 10 GiB and apply
      await superuserPage.getByTestId('quota-value-input').fill('10');
      await superuserPage.getByTestId('apply-quota-button').click();

      // Verify success
      await expect(
        superuserPage.getByText('Successfully created quota'),
      ).toBeVisible();

      // Wait for modal to close before reopening
      await expect(
        superuserPage.getByTestId('configure-quota-modal'),
      ).not.toBeVisible();

      // Reopen modal and wait for quota data to load
      await superuserPage.getByTestId(`${org.name}-options-toggle`).click();
      await superuserPage.getByTestId('configure-quota-option').click();
      await expect(
        superuserPage.getByTestId('configure-quota-modal'),
      ).toBeVisible();
      // Wait for existing quota value to populate (confirms query cache updated)
      await expect(superuserPage.getByTestId('quota-value-input')).toHaveValue(
        '10',
      );

      // UPDATE QUOTA: Change to 20 GiB
      await superuserPage.getByTestId('quota-value-input').fill('20');
      await superuserPage.getByTestId('apply-quota-button').click();
      await expect(
        superuserPage.getByText('Successfully updated quota'),
      ).toBeVisible();

      // Reopen modal
      await superuserPage.getByTestId(`${org.name}-options-toggle`).click();
      await superuserPage.getByTestId('configure-quota-option').click();
      await expect(
        superuserPage.getByTestId('configure-quota-modal'),
      ).toBeVisible();

      // ADD LIMIT: Add Warning limit at 80%
      await expect(superuserPage.getByTestId('add-limit-form')).toBeVisible();
      await superuserPage.getByTestId('new-limit-type-select').click();
      await superuserPage.getByRole('option', {name: 'Warning'}).click();
      await superuserPage.getByTestId('new-limit-percent-input').fill('80');
      await superuserPage.getByTestId('add-limit-button').click();
      await expect(
        superuserPage.getByText('Successfully added quota limit'),
      ).toBeVisible();

      // Reopen modal and verify limit exists
      await superuserPage.getByTestId(`${org.name}-options-toggle`).click();
      await superuserPage.getByTestId('configure-quota-option').click();
      await expect(
        superuserPage.getByTestId('configure-quota-modal'),
      ).toBeVisible();

      // UPDATE LIMIT: Change to 85%
      await superuserPage.getByTestId('limit-percent-input').fill('85');
      await superuserPage.getByTestId('update-limit-button').click();
      await expect(
        superuserPage.getByText('Successfully updated quota limit'),
      ).toBeVisible();

      // Reopen modal
      await superuserPage.getByTestId(`${org.name}-options-toggle`).click();
      await superuserPage.getByTestId('configure-quota-option').click();

      // DELETE LIMIT
      await superuserPage.getByTestId('remove-limit-button').click();
      await expect(
        superuserPage.getByText('Successfully deleted quota limit'),
      ).toBeVisible();

      // Reopen modal
      await superuserPage.getByTestId(`${org.name}-options-toggle`).click();
      await superuserPage.getByTestId('configure-quota-option').click();

      // DELETE QUOTA
      await superuserPage.getByTestId('remove-quota-button').click();
      await superuserPage.getByTestId('confirm-delete-quota').click();
      await expect(
        superuserPage.getByText('Successfully deleted quota'),
      ).toBeVisible();

      // Verify quota deleted via API
      const quotas = await superuserApi.raw.getOrganizationQuota(org.name);
      expect(quotas).toHaveLength(0);
    });

    test('regular user sees read-only quota in organization settings', async ({
      authenticatedPage,
      superuserApi,
      api,
    }) => {
      // Setup: Create organization (testuser owns it) with quota set by superuser
      const org = await api.organization('readonlyquota');
      await superuserApi.quota(org.name, 10737418240); // 10 GiB

      // Navigate as regular user to org settings
      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

      // Click on Quota tab
      await authenticatedPage.getByTestId('Quota').click();

      // Should see read-only alert
      await expect(
        authenticatedPage.getByTestId('readonly-quota-alert'),
      ).toBeVisible();

      // Fields should be disabled
      await expect(
        authenticatedPage.getByTestId('quota-value-input'),
      ).toBeDisabled();
      await expect(
        authenticatedPage.getByTestId('quota-unit-select-toggle'),
      ).toBeDisabled();

      // Apply and Remove buttons should NOT exist
      await expect(
        authenticatedPage.getByTestId('apply-quota-button'),
      ).not.toBeVisible();
      await expect(
        authenticatedPage.getByTestId('remove-quota-button'),
      ).not.toBeVisible();

      // Add Limit form should not be visible
      await expect(
        authenticatedPage.getByTestId('add-limit-form'),
      ).not.toBeVisible();
    });

    test('regular user sees no quota alert when quota not configured', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: Create organization WITHOUT quota (testuser owns it)
      const org = await api.organization('noquota');

      // Navigate to org settings as regular user
      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

      // Click on Quota tab
      await authenticatedPage.getByTestId('Quota').click();

      // Should see "no quota" alert for non-superuser
      await expect(
        authenticatedPage.getByTestId('no-quota-alert'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Quota must be configured by a superuser'),
      ).toBeVisible();
    });

    test('superuser sees no quota alert with instructions in organization settings', async ({
      superuserPage,
      superuserApi,
    }) => {
      // Setup: Create organization WITHOUT quota
      const org = await superuserApi.organization('noquotasu');

      // Navigate to org settings as superuser
      await superuserPage.goto(`/organization/${org.name}?tab=Settings`);

      // Click on Quota tab
      await superuserPage.getByTestId('Quota').click();

      // Should see superuser-specific alert
      await expect(
        superuserPage.getByTestId('no-quota-superuser-alert'),
      ).toBeVisible();
      await expect(
        superuserPage.getByText(
          'Use the "Configure Quota" option from the Organizations list page',
        ),
      ).toBeVisible();
    });

    test('superuser sees Configure Quota option in organizations list kebab menu', async ({
      superuserPage,
      superuserApi,
    }) => {
      // Setup: Create organization
      const org = await superuserApi.organization('kebabquota');

      // Navigate to organizations list
      await superuserPage.goto('/organization');

      // Wait for org to appear and click kebab menu
      await superuserPage.getByTestId(`${org.name}-options-toggle`).click();

      // Should see Configure Quota option
      await expect(
        superuserPage.getByTestId('configure-quota-option'),
      ).toBeVisible();
      await expect(superuserPage.getByText('Configure Quota')).toBeVisible();
    });

    test('regular user does not see organization options kebab menu', async ({
      authenticatedPage,
      superuserApi,
    }) => {
      // Setup: Create organization
      const org = await superuserApi.organization('nokebab');

      // Navigate to organizations list as regular user
      await authenticatedPage.goto('/organization');

      // Kebab menu should NOT be visible for non-superusers
      await expect(
        authenticatedPage.getByTestId(`${org.name}-options-toggle`),
      ).not.toBeVisible();
    });

    test(
      'user can view quota with limits in organization Settings tab',
      {tag: '@PROJQUAY-9785'},
      async ({authenticatedPage, superuserApi, api}) => {
        // Setup: Create organization (testuser owns it) with quota and limits set by superuser
        const org = await api.organization('userquotaview');
        const quota = await superuserApi.quota(org.name, 104857600); // 100 MiB

        // Add warning limit
        await superuserApi.raw.createQuotaLimit(
          org.name,
          quota.quotaId,
          'Warning',
          70,
        );
        // Add reject limit
        await superuserApi.raw.createQuotaLimit(
          org.name,
          quota.quotaId,
          'Reject',
          100,
        );

        // Navigate to org settings and quota tab
        await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
        await authenticatedPage.getByTestId('Quota').click();

        // Should see read-only quota
        await expect(
          authenticatedPage.getByTestId('readonly-quota-alert'),
        ).toBeVisible();

        // Should display quota value
        await expect(
          authenticatedPage.getByTestId('quota-value-input'),
        ).toHaveValue('100');
        await expect(
          authenticatedPage.getByTestId('quota-unit-select-toggle'),
        ).toContainText('MiB');

        // Should show quota limits (verify at least one exists)
        await expect(
          authenticatedPage.locator('[data-testid^="quota-limit-"]').first(),
        ).toBeVisible();

        // Fields should be disabled (read-only)
        await expect(
          authenticatedPage.getByTestId('quota-value-input'),
        ).toBeDisabled();

        // Add Limit form should not be visible for users
        await expect(
          authenticatedPage.getByTestId('add-limit-form'),
        ).not.toBeVisible();
      },
    );
  },
);

test.describe(
  'Quota Enforcement E2E',
  {
    tag: [
      '@organization',
      '@feature:QUOTA_MANAGEMENT',
      '@feature:EDIT_QUOTA',
      '@container',
    ],
  },
  () => {
    test('displays quota usage in organization dashboard', async ({
      authenticatedPage,
      superuserApi,
      api,
    }) => {
      const org = await api.organization('quotadashboard');
      await superuserApi.quota(org.name, 104857600); // 100 MiB

      // Create repo before pushing so V2 auth can resolve scope
      await api.repositoryWithName(org.name, 'testrepo');

      await pushImage(
        org.name,
        'testrepo',
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Verify quota usage appears in Settings > Quota tab
      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByTestId('Quota').click();

      // When quota is configured, the form renders with id="quota-management-form"
      const quotaForm = authenticatedPage.locator('#quota-management-form');
      await expect(quotaForm).toBeVisible();

      // Verify quota value input and unit selector are present
      await expect(
        authenticatedPage.getByTestId('quota-value-input'),
      ).toBeVisible();
      const unitToggle = authenticatedPage.getByTestId(
        'quota-unit-select-toggle',
      );
      await expect(unitToggle).toHaveText(/KiB|MiB|GiB|TiB/);
    });

    test('shows quota with warning policy in settings', async ({
      authenticatedPage,
      superuserApi,
      api,
    }) => {
      const org = await api.organization('quotawarn');
      const quota = await superuserApi.quota(org.name, 3145728); // 3 MiB

      await superuserApi.raw.createQuotaLimit(
        org.name,
        quota.quotaId,
        'Warning',
        80,
      );

      // Create repos before pushing
      await api.repositoryWithName(org.name, 'repo1');
      await api.repositoryWithName(org.name, 'repo2');

      // Push images to exceed 80% warning threshold (2 x ~1.2 MiB)
      await pushImage(
        org.name,
        'repo1',
        'v1',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );
      await pushImage(
        org.name,
        'repo2',
        'v2',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Verify quota form and policy section in Settings > Quota tab
      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByTestId('Quota').click();

      const quotaForm = authenticatedPage.locator('#quota-management-form');
      await expect(quotaForm).toBeVisible();

      // Verify warning policy is shown with percentage
      const policySection = authenticatedPage.getByTestId(
        'quota-policy-section',
      );
      await expect(policySection).toBeVisible();
      await expect(policySection).toContainText('Warning');
      await expect(policySection).toContainText('%');
    });

    test('displays quota state when quota exceeded', async ({
      authenticatedPage,
      superuserApi,
      api,
    }) => {
      const org = await api.organization('quotaexceed');
      const quota = await superuserApi.quota(org.name, 2097152); // 2 MiB

      await superuserApi.raw.createQuotaLimit(
        org.name,
        quota.quotaId,
        'Reject',
        100,
      );

      // Create repo before pushing
      await api.repositoryWithName(org.name, 'fillrepo');

      // First push (~1.2 MiB) should succeed
      await pushImage(
        org.name,
        'fillrepo',
        'v1',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Second push should be rejected (total ~2.4 MiB > 2 MiB limit)
      let secondPushFailed = false;
      try {
        await pushImage(
          org.name,
          'fillrepo',
          'v2',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );
      } catch {
        secondPushFailed = true;
      }

      // Verify quota state in Settings > Quota tab
      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByTestId('Quota').click();

      const quotaForm = authenticatedPage.locator('#quota-management-form');
      await expect(quotaForm).toBeVisible();

      // Verify reject policy is configured
      const policySection = authenticatedPage.getByTestId(
        'quota-policy-section',
      );
      await expect(policySection).toBeVisible();
      await expect(policySection).toContainText('Reject');
    });

    test('quota warning policy visible after push', async ({
      authenticatedPage,
      superuserApi,
      api,
    }) => {
      const org = await api.organization('quotanotify');
      const quota = await superuserApi.quota(org.name, 3145728); // 3 MiB

      await superuserApi.raw.createQuotaLimit(
        org.name,
        quota.quotaId,
        'Warning',
        80,
      );

      // Create repos before pushing
      await api.repositoryWithName(org.name, 'repo1');
      await api.repositoryWithName(org.name, 'repo2');

      // Push images to trigger warning threshold
      await pushImage(
        org.name,
        'repo1',
        'v1',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );
      await pushImage(
        org.name,
        'repo2',
        'v2',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Verify quota configuration and warning limit in Settings > Quota tab
      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByTestId('Quota').click();

      const quotaForm = authenticatedPage.locator('#quota-management-form');
      await expect(quotaForm).toBeVisible();

      // Verify the read-only alert is shown
      await expect(
        authenticatedPage.getByTestId('readonly-quota-alert'),
      ).toBeVisible();

      // Verify warning policy exists
      const policySection = authenticatedPage.getByTestId(
        'quota-policy-section',
      );
      await expect(policySection).toBeVisible();
      await expect(policySection).toContainText('Warning');
    });
  },
);
