import {test, expect} from '../../fixtures';

test.describe(
  'Superuser Framework',
  {tag: '@feature:SUPERUSERS_FULL_ACCESS'},
  () => {
    test('superuser can navigate to all superuser pages', async ({
      superuserPage,
    }) => {
      const pages = [
        {path: '/service-keys', heading: 'Service Keys'},
        {path: '/change-log', heading: 'Change Log'},
        {path: '/usage-logs', heading: 'Usage Logs'},
        {path: '/messages', heading: 'Messages'},
      ];

      for (const {path, heading} of pages) {
        await superuserPage.goto(path);
        await expect(
          superuserPage.getByRole('heading', {name: heading}),
        ).toBeVisible();
      }
    });

    test('superuser sees navigation items and can expand section', async ({
      superuserPage,
    }) => {
      await superuserPage.goto('/organization');

      // Verify Superuser section exists and expand it
      const superuserNavSection = superuserPage.getByRole('button', {
        name: 'Superuser',
      });
      await expect(superuserNavSection).toBeVisible();
      await superuserNavSection.click();

      // Verify all nav items are visible
      await expect(superuserPage.getByTestId('service-keys-nav')).toBeVisible();
      await expect(superuserPage.getByTestId('change-log-nav')).toBeVisible();
      await expect(superuserPage.getByTestId('usage-logs-nav')).toBeVisible();
      await expect(superuserPage.getByTestId('messages-nav')).toBeVisible();

      // Test navigation works
      await superuserPage.getByTestId('service-keys-nav').click();
      await expect(superuserPage).toHaveURL(/.*\/service-keys.*/);
    });

    test('superuser sees Settings column and organization actions menu', async ({
      superuserPage,
      superuserApi,
    }) => {
      // Create test organization
      const org = await superuserApi.organization('fwtest');

      await superuserPage.goto('/organization');

      // Verify Settings column header
      await expect(
        superuserPage.getByRole('columnheader', {name: 'Settings'}),
      ).toBeVisible();

      // Verify options toggle exists for the created org
      const optionsToggle = superuserPage.getByTestId(
        `${org.name}-options-toggle`,
      );
      await expect(optionsToggle).toBeVisible({timeout: 15000});

      // Click and verify menu items
      await optionsToggle.click();
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

    test('regular user does not see superuser features', async ({
      authenticatedPage,
      superuserApi,
    }) => {
      // Create org via superuser API for visibility test
      const org = await superuserApi.organization('regulartest');

      await authenticatedPage.goto('/organization');

      // Verify Superuser nav section is NOT visible
      await expect(
        authenticatedPage.getByRole('button', {name: 'Superuser'}),
      ).not.toBeVisible();

      // Verify Settings column is NOT visible
      await expect(
        authenticatedPage.getByRole('columnheader', {name: 'Settings'}),
      ).not.toBeVisible();

      // Verify no options toggle for organizations
      await expect(
        authenticatedPage.getByTestId(`${org.name}-options-toggle`),
      ).not.toBeVisible();

      // Verify direct navigation to superuser pages redirects away
      await authenticatedPage.goto('/service-keys');
      await expect(authenticatedPage).toHaveURL(
        /.*\/(organization|repository).*/,
      );

      // Also verify other superuser pages redirect
      await authenticatedPage.goto('/change-log');
      await expect(authenticatedPage).toHaveURL(
        /.*\/(organization|repository).*/,
      );
    });
  },
);
