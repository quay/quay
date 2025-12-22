/**
 * Quota Management E2E Tests
 *
 * Tests for storage quota management including:
 * - Superuser quota lifecycle (create, update, add limit, delete)
 * - Regular user read-only view
 * - Configure Quota modal access from organizations list
 *
 * Requires QUOTA_MANAGEMENT and EDIT_QUOTA features to be enabled.
 *
 * Migrated from: web/cypress/e2e/quota.cy.ts (27 tests consolidated to 7)
 */

import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

test.describe(
  'Quota Management',
  {tag: ['@organization', '@feature:QUOTA_MANAGEMENT', '@feature:EDIT_QUOTA']},
  () => {
    test(
      'superuser can configure quota lifecycle: create, update, add limit, update limit, delete limit, delete quota',
      {tag: '@feature:SUPERUSERS_FULL_ACCESS'},
      async ({superuserPage, superuserApi}) => {
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
        await expect(
          superuserPage.getByTestId('quota-value-input'),
        ).toHaveValue('10');

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
        await expect(
          superuserPage.getByRole('heading', {name: 'Delete Quota'}),
        ).toBeVisible();
        await superuserPage.getByRole('button', {name: 'OK'}).click();
        await expect(
          superuserPage.getByText('Successfully deleted quota'),
        ).toBeVisible();

        // Verify quota deleted via API
        const quotas = await superuserApi.raw.getOrganizationQuota(org.name);
        expect(quotas).toHaveLength(0);
      },
    );

    test('regular user sees read-only quota in organization settings', async ({
      authenticatedPage,
      superuserApi,
    }) => {
      // Setup: Create organization with quota (using superuser)
      const org = await superuserApi.organization('readonlyquota');
      await superuserApi.quota(org.name, 10737418240); // 10 GiB
      // Add testuser as org admin so they can see Settings
      const team = await superuserApi.team(org.name, 'admins', 'admin');
      await superuserApi.teamMember(
        org.name,
        team.name,
        TEST_USERS.user.username,
      );

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
      superuserApi,
    }) => {
      // Setup: Create organization WITHOUT quota
      const org = await superuserApi.organization('noquota');
      // Add testuser as org admin so they can see Settings
      const team = await superuserApi.team(org.name, 'admins', 'admin');
      await superuserApi.teamMember(
        org.name,
        team.name,
        TEST_USERS.user.username,
      );

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

    test(
      'superuser sees no quota alert with instructions in organization settings',
      {tag: '@feature:SUPERUSERS_FULL_ACCESS'},
      async ({superuserPage, superuserApi}) => {
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
      },
    );

    test(
      'superuser sees Configure Quota option in organizations list kebab menu',
      {tag: '@feature:SUPERUSERS_FULL_ACCESS'},
      async ({superuserPage, superuserApi}) => {
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
      },
    );

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
      async ({authenticatedPage, superuserApi}) => {
        // Setup: Create organization with quota and limits
        const org = await superuserApi.organization('userquotaview');
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

        // Add testuser as org admin so they can see Settings
        const team = await superuserApi.team(org.name, 'admins', 'admin');
        await superuserApi.teamMember(
          org.name,
          team.name,
          TEST_USERS.user.username,
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
