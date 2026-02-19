import {test, expect, uniqueName} from '../../fixtures';

test.describe(
  'Superuser Organization Actions',
  {tag: ['@superuser', '@feature:SUPERUSERS_FULL_ACCESS']},
  () => {
    test('superuser can rename an organization', async ({
      superuserPage,
      superuserApi,
    }) => {
      const org = await superuserApi.organization('renametest');
      const newName = uniqueName('renamed');

      await superuserPage.goto('/organization');

      // Open kebab menu
      const optionsToggle = superuserPage.getByTestId(
        `${org.name}-options-toggle`,
      );
      await expect(optionsToggle).toBeVisible({timeout: 15000});
      await optionsToggle.click();

      await superuserPage
        .getByRole('menuitem', {name: 'Rename Organization'})
        .click();

      // Modal should open with OK disabled (empty input)
      const dialog = superuserPage.getByRole('dialog');
      await expect(dialog).toBeVisible();
      await expect(dialog.getByRole('button', {name: 'OK'})).toBeDisabled();

      // Fill in new name - OK should become enabled
      await superuserPage.locator('#new-organization-name').fill(newName);
      await expect(dialog.getByRole('button', {name: 'OK'})).toBeEnabled();

      // Clear and verify OK is disabled again
      await superuserPage.locator('#new-organization-name').fill('');
      await expect(dialog.getByRole('button', {name: 'OK'})).toBeDisabled();

      // Fill final name and submit
      await superuserPage.locator('#new-organization-name').fill(newName);
      await dialog.getByRole('button', {name: 'OK'}).click();

      // Modal closes immediately, success alert appears
      await expect(dialog).not.toBeVisible();
      await expect(
        superuserPage.getByText(`Successfully renamed organization`),
      ).toBeVisible();

      // New name should appear in the list
      await expect(
        superuserPage.getByTestId(`${newName}-options-toggle`),
      ).toBeVisible({timeout: 15000});

      // Clean up the renamed org (auto-cleanup will try original name and fail silently)
      await superuserApi.raw.deleteOrganization(newName);
    });

    test('superuser can delete an organization', async ({
      superuserPage,
      superuserApi,
    }) => {
      const org = await superuserApi.organization('deletetest');

      await superuserPage.goto('/organization');

      const optionsToggle = superuserPage.getByTestId(
        `${org.name}-options-toggle`,
      );
      await expect(optionsToggle).toBeVisible({timeout: 15000});
      await optionsToggle.click();

      await superuserPage
        .getByRole('menuitem', {name: 'Delete Organization'})
        .click();

      // Confirmation modal should open
      const dialog = superuserPage.getByRole('dialog');
      await expect(dialog).toBeVisible();
      await expect(
        dialog.getByText('Are you sure you want to delete this organization'),
      ).toBeVisible();

      // Confirm deletion
      await dialog.getByRole('button', {name: 'OK'}).click();

      // Modal closes, success alert appears
      await expect(dialog).not.toBeVisible();
      await expect(
        superuserPage.getByText(
          `Successfully deleted organization ${org.name}`,
        ),
      ).toBeVisible();

      // Org should no longer appear in the list
      await expect(
        superuserPage.getByTestId(`${org.name}-options-toggle`),
      ).not.toBeVisible();
    });

    test('superuser can take ownership of an organization', async ({
      superuserPage,
      api,
    }) => {
      // Create org as regular user so superuser doesn't own it
      const org = await api.organization('ownertest');

      await superuserPage.goto('/organization');

      const optionsToggle = superuserPage.getByTestId(
        `${org.name}-options-toggle`,
      );
      await expect(optionsToggle).toBeVisible({timeout: 15000});
      await optionsToggle.click();

      await superuserPage
        .getByRole('menuitem', {name: 'Take Ownership'})
        .click();

      // Confirmation modal should open
      const dialog = superuserPage.getByRole('dialog');
      await expect(dialog).toBeVisible();
      await expect(
        dialog.getByText('Are you sure you want to take ownership of'),
      ).toBeVisible();
      await expect(dialog.getByText(org.name)).toBeVisible();

      // Confirm take ownership
      await dialog.getByRole('button', {name: 'Take Ownership'}).click();

      // On success the app navigates to the org detail page
      await expect(dialog).not.toBeVisible();
      await expect(superuserPage).toHaveURL(
        new RegExp(`/organization/${org.name}`),
      );

      // Verify ownership: superuser (admin) should appear in the owners team
      await superuserPage
        .getByRole('tab', {name: 'Teams and membership'})
        .click();
      await expect(superuserPage.getByText('owners')).toBeVisible();
      await expect(
        superuserPage.getByTestId('owners-team-dropdown-toggle'),
      ).toBeVisible();
    });
  },
);
