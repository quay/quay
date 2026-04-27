import {test, expect} from '../../fixtures';

test.describe(
  'Superuser User Management',
  {
    tag: ['@superuser', '@feature:SUPERUSERS_FULL_ACCESS', '@auth:Database'],
  },
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

    test('create user modal opens with username and email fields', async ({
      superuserPage,
    }) => {
      await superuserPage.goto('/organization');

      await superuserPage.getByRole('button', {name: 'Create User'}).click();

      // Modal should appear
      await expect(
        superuserPage.getByRole('heading', {name: 'Create New User'}),
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

    test('superuser can create a user via API and see it in list', async ({
      superuserPage,
      superuserApi,
    }) => {
      const user = await superuserApi.user('testsu');

      await superuserPage.goto('/organization');

      // User should appear in the list (use first() since superuser view
      // may show the same user in both org and user sections)
      await expect(
        superuserPage.getByRole('link', {name: user.username}).first(),
      ).toBeVisible();
    });

    test('superuser sees user management actions in kebab menu', async ({
      superuserPage,
      superuserApi,
    }) => {
      const user = await superuserApi.user('testmgmt');

      await superuserPage.goto('/organization');

      // Open kebab for the user
      await superuserPage
        .getByTestId(`${user.username}-options-toggle`)
        .click();

      // Should see management options
      await expect(superuserPage.getByText('Disable User')).toBeVisible();
      await expect(superuserPage.getByText('Delete User')).toBeVisible();
    });
  },
);
