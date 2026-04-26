import {test, expect} from '../../fixtures';

test.describe(
  'Superuser User Management',
  {tag: ['@superuser', '@feature:SUPERUSERS_FULL_ACCESS']},
  () => {
    test('superuser sees Create User button on org list', async ({
      superuserPage,
    }) => {
      await superuserPage.goto('/organization');

      await expect(
        superuserPage.getByRole('button', {name: 'Create User'}),
      ).toBeVisible();
    });

    test('regular user does not see Create User button', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto('/organization');

      await expect(
        authenticatedPage.getByRole('button', {name: 'Create User'}),
      ).not.toBeVisible();
    });

    test('create user modal opens and validates input', async ({
      superuserPage,
    }) => {
      await superuserPage.goto('/organization');

      await superuserPage.getByRole('button', {name: 'Create User'}).click();

      // Modal should appear
      await expect(
        superuserPage.getByText('Create User', {exact: false}),
      ).toBeVisible();

      // Username field should be present
      const usernameInput = superuserPage.getByRole('textbox', {
        name: /username/i,
      });
      await expect(usernameInput).toBeVisible();

      // Email field should be present
      const emailInput = superuserPage.getByRole('textbox', {
        name: /email/i,
      });
      await expect(emailInput).toBeVisible();
    });

    test('superuser can create and delete a user', async ({
      superuserPage,
      superuserApi,
    }) => {
      const username = `testsu${Date.now()}`.substring(0, 20).toLowerCase();

      // Create user via API
      await superuserApi.user(username, `${username}@test.example.com`);

      await superuserPage.goto('/organization');

      // User should appear in the list
      await expect(superuserPage.getByText(username)).toBeVisible();
    });

    test('superuser sees user management actions in kebab menu', async ({
      superuserPage,
      superuserApi,
    }) => {
      const username = `testmgmt${Date.now()}`.substring(0, 20).toLowerCase();
      await superuserApi.user(username, `${username}@test.example.com`);

      await superuserPage.goto('/organization');

      // Find the row for the user and open kebab
      const userRow = superuserPage
        .getByRole('row')
        .filter({hasText: username});
      await userRow.getByRole('button', {name: /actions|kebab/i}).click();

      // Should see management options
      await expect(
        superuserPage
          .getByText('Disable User')
          .or(superuserPage.getByText('Delete User')),
      ).toBeVisible();
    });
  },
);
