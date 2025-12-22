/**
 * Superuser Organization Actions E2E Tests
 *
 * Tests for superuser organization management including:
 * - Access control (superuser vs regular user visibility)
 * - Rename organization
 * - Delete organization
 * - Take ownership
 *
 * Requires SUPERUSERS_FULL_ACCESS feature to be enabled.
 *
 * Migrated from: web/cypress/e2e/superuser-org-actions.cy.ts (12 tests consolidated to 5)
 */

import {test, expect, uniqueName} from '../../fixtures';

test.describe(
  'Superuser Organization Actions',
  {tag: '@feature:SUPERUSERS_FULL_ACCESS'},
  () => {
    test('superuser sees actions column and options menu for organizations', async ({
      superuserPage,
      superuserApi,
    }) => {
      // Setup: Create organization
      const org = await superuserApi.organization('suorgtest');

      // Navigate to organizations list
      await superuserPage.goto('/organization');

      // Verify Settings column header is visible
      await expect(
        superuserPage.getByRole('columnheader', {name: 'Settings'}),
      ).toBeVisible();

      // Verify kebab menu toggle exists for the organization
      const optionsToggle = superuserPage.getByTestId(
        `${org.name}-options-toggle`,
      );
      await expect(optionsToggle).toBeVisible();

      // Click kebab menu to verify menu items
      await optionsToggle.click();

      // Verify all expected menu items are visible
      await expect(
        superuserPage.getByRole('menuitem', {name: 'Rename Organization'}),
      ).toBeVisible();
      await expect(
        superuserPage.getByRole('menuitem', {name: 'Delete Organization'}),
      ).toBeVisible();
      await expect(
        superuserPage.getByRole('menuitem', {name: 'Take Ownership'}),
      ).toBeVisible();
    });

    test('regular user does not see organization options menu', async ({
      authenticatedPage,
      superuserApi,
    }) => {
      // Setup: Create organization via superuser (regular user cannot create orgs)
      const org = await superuserApi.organization('regulartest');

      // Navigate to organizations list as regular user
      await authenticatedPage.goto('/organization');

      // Kebab menu should NOT be visible for non-superusers
      await expect(
        authenticatedPage.getByTestId(`${org.name}-options-toggle`),
      ).not.toBeVisible();

      // Settings column header should also not be visible
      await expect(
        authenticatedPage.getByRole('columnheader', {name: 'Settings'}),
      ).not.toBeVisible();
    });

    test('superuser can rename organization', async ({
      superuserPage,
      superuserApi,
    }) => {
      // Setup: Create organization
      const org = await superuserApi.organization('renametest');
      const newName = uniqueName('renamed');

      // Navigate to organizations list
      await superuserPage.goto('/organization');

      // Click kebab menu
      await superuserPage.getByTestId(`${org.name}-options-toggle`).click();

      // Click Rename Organization
      await superuserPage
        .getByRole('menuitem', {name: 'Rename Organization'})
        .click();

      // Verify modal opens
      const modal = superuserPage.getByRole('dialog');
      await expect(modal).toBeVisible();
      await expect(
        superuserPage.getByRole('heading', {name: 'Rename Organization'}),
      ).toBeVisible();

      // Verify OK button is disabled when input is empty
      const okButton = superuserPage.getByRole('button', {name: 'OK'});
      await expect(okButton).toBeDisabled();

      // Fill in new name
      await superuserPage.locator('#new-organization-name').fill(newName);

      // OK button should now be enabled
      await expect(okButton).toBeEnabled();

      // Submit form
      await okButton.click();

      // Modal should close
      await expect(modal).not.toBeVisible();

      // Wait for success alert to confirm API completed
      await expect(
        superuserPage.getByText(/Successfully renamed organization/),
      ).toBeVisible({timeout: 10000});

      // Reload page to see updated list (query cache may not update immediately)
      await superuserPage.reload();

      // Verify the new org name appears in the list
      await expect(
        superuserPage.getByTestId(`${newName}-options-toggle`),
      ).toBeVisible({timeout: 10000});

      // Old org name should no longer exist
      await expect(
        superuserPage.getByTestId(`${org.name}-options-toggle`),
      ).not.toBeVisible();

      // Cleanup: Manually delete the renamed org since TestApi tracked the old name
      // The renamed org won't be auto-cleaned by superuserApi
      await superuserApi.raw.deleteOrganization(newName);
    });

    test('superuser can delete organization', async ({
      superuserPage,
      superuserApi,
    }) => {
      // Setup: Create organization
      const org = await superuserApi.organization('deletetest');

      // Navigate to organizations list
      await superuserPage.goto('/organization');

      // Wait for org to appear (may take time with parallel test execution)
      await expect(
        superuserPage.getByTestId(`${org.name}-options-toggle`),
      ).toBeVisible({timeout: 15000});

      // Click kebab menu
      await superuserPage.getByTestId(`${org.name}-options-toggle`).click();

      // Click Delete Organization
      await superuserPage
        .getByRole('menuitem', {name: 'Delete Organization'})
        .click();

      // Verify modal opens with confirmation text
      const modal = superuserPage.getByRole('dialog');
      await expect(modal).toBeVisible();
      await expect(
        superuserPage.getByRole('heading', {name: 'Delete Organization'}),
      ).toBeVisible();
      await expect(
        superuserPage.getByText(
          'Are you sure you want to delete this organization',
        ),
      ).toBeVisible();

      // Confirm deletion
      await superuserPage.getByRole('button', {name: 'OK'}).click();

      // Modal should close
      await expect(modal).not.toBeVisible();

      // Wait for success alert to confirm API completed
      await expect(
        superuserPage.getByText(/Successfully deleted organization/),
      ).toBeVisible({timeout: 10000});

      // Reload page to ensure list is updated
      await superuserPage.reload();

      // Org should no longer appear in list
      await expect(
        superuserPage.getByTestId(`${org.name}-options-toggle`),
      ).not.toBeVisible();
    });

    test('superuser can take ownership of organization', async ({
      superuserPage,
      superuserApi,
    }) => {
      // Setup: Create organization
      const org = await superuserApi.organization('takeowntest');

      // Navigate to organizations list
      await superuserPage.goto('/organization');

      // Click kebab menu
      await superuserPage.getByTestId(`${org.name}-options-toggle`).click();

      // Click Take Ownership
      await superuserPage
        .getByRole('menuitem', {name: 'Take Ownership'})
        .click();

      // Verify modal opens with confirmation text
      const modal = superuserPage.getByRole('dialog');
      await expect(modal).toBeVisible();
      await expect(
        superuserPage.getByRole('heading', {name: 'Take Ownership'}),
      ).toBeVisible();
      // Check for the confirmation text including the org name within the modal
      await expect(
        modal.getByText(/Are you sure you want to take ownership of/),
      ).toBeVisible();
      await expect(modal.locator('strong', {hasText: org.name})).toBeVisible();

      // Confirm take ownership
      await superuserPage.getByRole('button', {name: 'Take Ownership'}).click();

      // After take ownership, the page navigates to the organization detail page
      // Wait for URL to change to the org page
      await superuserPage.waitForURL(`**/organization/${org.name}**`);

      // Verify we're on the organization page
      await expect(superuserPage).toHaveURL(
        new RegExp(`/organization/${org.name}`),
      );
    });
  },
);
