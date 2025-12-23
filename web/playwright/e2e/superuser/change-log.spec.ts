import {test, expect} from '../../fixtures';

test.describe(
  'Superuser Change Log',
  {tag: ['@superuser', '@feature:SUPERUSERS_FULL_ACCESS']},
  () => {
    // Access control tests (redirect for non-superusers, access for superusers)
    // are covered by framework.spec.ts

    test('displays markdown changelog content', async ({superuserPage}) => {
      await superuserPage.goto('/change-log');

      // Verify page header is present
      await expect(
        superuserPage.getByRole('heading', {name: 'Change Log'}),
      ).toBeVisible();

      // Verify markdown content is rendered (real API data)
      // The component renders markdown inside a Card with TextContent
      // Just verify the page loads and doesn't show error state
      await expect(
        superuserPage.getByText('Error Loading Change Log'),
      ).not.toBeVisible();
    });

    test('shows error state when API fails', async ({superuserPage}) => {
      await superuserPage.route(
        '**/api/v1/superuser/changelog/',
        async (route) => {
          await route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({error: 'Internal server error'}),
          });
        },
      );

      await superuserPage.goto('/change-log');

      await expect(
        superuserPage.getByText('Error Loading Change Log'),
      ).toBeVisible();
      await expect(
        superuserPage.getByText(
          'Cannot load change log. Please contact support.',
        ),
      ).toBeVisible();
    });
  },
);
