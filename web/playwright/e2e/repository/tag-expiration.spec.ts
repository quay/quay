import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {pushImage} from '../../utils/container';

/**
 * Safely adds months to a date without JavaScript date rollover issues.
 */
function addMonthsSafe(date: Date, months: number): Date {
  const result = new Date(date);
  const targetMonth = result.getMonth() + months;
  const originalDay = result.getDate();
  result.setDate(1);
  result.setMonth(targetMonth);
  const lastDayOfMonth = new Date(
    result.getFullYear(),
    result.getMonth() + 1,
    0,
  ).getDate();
  result.setDate(Math.min(originalDay, lastDayOfMonth));
  return result;
}

test.describe(
  'Repository Details - Tag Expiration',
  {
    tag: [
      '@tags',
      '@repository',
      '@container',
      '@feature:CHANGE_TAG_EXPIRATION',
    ],
  },
  () => {
    test('change expiration via kebab and reset to never', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
      await expect(
        authenticatedPage.getByRole('link', {name: 'latest'}),
      ).toBeVisible();

      const latestRow = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: 'latest'}),
      });

      // Open expiration modal via kebab
      await latestRow.locator('#tag-actions-kebab').click();
      await authenticatedPage.getByText('Change expiration').click();

      const expirationTags = authenticatedPage
        .locator('#edit-expiration-tags')
        .first();
      await expect(expirationTags).toContainText('latest');

      // Select next month in date picker
      const nextMonth = addMonthsSafe(new Date(), 1);
      const sameDateNextMonthGB = nextMonth.toLocaleDateString('en-GB', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });

      await authenticatedPage
        .locator('[aria-label="Toggle date picker"]')
        .click();
      await authenticatedPage
        .locator('button[aria-label="Next month"]')
        .click();
      await authenticatedPage
        .locator(`[aria-label="${sameDateNextMonthGB}"]`)
        .click();

      // Set time
      nextMonth.setHours(1);
      nextMonth.setMinutes(0);
      const formattedTime = nextMonth.toLocaleTimeString(
        undefined, // Use default locale
        {hour: 'numeric', minute: '2-digit'},
      );

      await authenticatedPage.locator('#expiration-time-picker').click();
      await authenticatedPage
        .getByText(formattedTime.replace(/ AM| PM/, ''), {exact: false})
        .first()
        .click();

      await authenticatedPage.getByText('Change Expiration').click();

      // Verify expiration was set
      await expect(latestRow.locator('[data-label="Expires"]')).not.toHaveText(
        'Never',
      );

      // Reset to Never
      await latestRow.locator('#tag-actions-kebab').click();
      await authenticatedPage.getByText('Change expiration').click();
      await authenticatedPage.getByText('Clear').click();
      await authenticatedPage.getByText('Change Expiration').click();

      await expect(latestRow.locator('[data-label="Expires"]')).toHaveText(
        'Never',
      );
      await expect(
        authenticatedPage.getByText(
          'Successfully set expiration for tag latest to never',
        ),
      ).toBeVisible();
    });

    test('change expiration by clicking Expires column', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
      await expect(
        authenticatedPage.getByRole('link', {name: 'latest'}),
      ).toBeVisible();

      const latestRow = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: 'latest'}),
      });

      // Click "Never" in Expires column to open expiration modal
      await latestRow.getByText('Never').click();

      const expirationTags = authenticatedPage
        .locator('#edit-expiration-tags')
        .first();
      await expect(expirationTags).toContainText('latest');

      // Select next month
      const nextMonth = addMonthsSafe(new Date(), 1);
      const sameDateNextMonthGB = nextMonth.toLocaleDateString('en-GB', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });

      await authenticatedPage
        .locator('[aria-label="Toggle date picker"]')
        .click();
      await authenticatedPage
        .locator('button[aria-label="Next month"]')
        .click();
      await authenticatedPage
        .locator(`[aria-label="${sameDateNextMonthGB}"]`)
        .click();

      // Set time
      nextMonth.setHours(1);
      nextMonth.setMinutes(0);
      const formattedTime = nextMonth.toLocaleTimeString(undefined, {
        hour: 'numeric',
        minute: '2-digit',
      });

      await authenticatedPage.locator('#expiration-time-picker').click();
      await authenticatedPage
        .getByText(formattedTime.replace(/ AM| PM/, ''), {exact: false})
        .first()
        .click();

      await authenticatedPage.getByText('Change Expiration').click();

      await expect(latestRow.locator('[data-label="Expires"]')).not.toHaveText(
        'Never',
      );
    });

    test('bulk change tag expirations', async ({authenticatedPage, api}) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'tag1',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );
      await pushImage(
        repo.namespace,
        repo.name,
        'tag2',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
      await expect(
        authenticatedPage.getByRole('link', {name: 'tag1'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('link', {name: 'tag2'}),
      ).toBeVisible();

      // Select all tags
      await authenticatedPage.locator('#toolbar-dropdown-checkbox').click();
      await authenticatedPage.getByTestId('select-page-items-action').click();
      await authenticatedPage.getByTestId('bulk-actions-kebab').click();
      await authenticatedPage.getByText('Set expiration').click();

      const expirationTags = authenticatedPage
        .locator('#edit-expiration-tags')
        .first();
      await expect(expirationTags).toContainText('tag1');
      await expect(expirationTags).toContainText('tag2');

      // Select next month
      const nextMonth = addMonthsSafe(new Date(), 1);
      const sameDateNextMonthGB = nextMonth.toLocaleDateString('en-GB', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });

      await authenticatedPage
        .locator('[aria-label="Toggle date picker"]')
        .click();
      await authenticatedPage
        .locator('button[aria-label="Next month"]')
        .click();
      await authenticatedPage
        .locator(`[aria-label="${sameDateNextMonthGB}"]`)
        .click();

      nextMonth.setHours(1);
      nextMonth.setMinutes(0);
      const formattedTime = nextMonth.toLocaleTimeString(undefined, {
        hour: 'numeric',
        minute: '2-digit',
      });

      await authenticatedPage.locator('#expiration-time-picker').click();
      await authenticatedPage
        .getByText(formattedTime.replace(/ AM| PM/, ''), {exact: false})
        .first()
        .click();

      await authenticatedPage.getByText('Change Expiration').click();

      // Verify both tags show expiration
      const tag1Row = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: 'tag1'}),
      });
      await expect(tag1Row.locator('[data-label="Expires"]')).not.toHaveText(
        'Never',
      );

      const tag2Row = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: 'tag2'}),
      });
      await expect(tag2Row.locator('[data-label="Expires"]')).not.toHaveText(
        'Never',
      );

      await expect(
        authenticatedPage.getByText(/Successfully updated tag expirations/),
      ).toBeVisible();
    });

    test('alert on failure to change expiration', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Mock error for tag expiration update
      await authenticatedPage.route(
        `**/api/v1/repository/${repo.namespace}/${repo.name}/tag/latest`,
        async (route) => {
          if (route.request().method() === 'PUT') {
            await route.fulfill({status: 500});
          } else {
            await route.continue();
          }
        },
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
      await expect(
        authenticatedPage.getByRole('link', {name: 'latest'}),
      ).toBeVisible();

      const latestRow = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: 'latest'}),
      });

      // Click "Never" to open expiration modal
      await latestRow.getByText('Never').click();

      const nextMonth = addMonthsSafe(new Date(), 1);
      const sameDateNextMonthGB = nextMonth.toLocaleDateString('en-GB', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });

      await authenticatedPage
        .locator('[aria-label="Toggle date picker"]')
        .click();
      await authenticatedPage
        .locator('button[aria-label="Next month"]')
        .click();
      await authenticatedPage
        .locator(`[aria-label="${sameDateNextMonthGB}"]`)
        .click();

      nextMonth.setHours(1);
      nextMonth.setMinutes(0);
      const formattedTime = nextMonth.toLocaleTimeString(undefined, {
        hour: 'numeric',
        minute: '2-digit',
      });

      await authenticatedPage.locator('#expiration-time-picker').click();
      await authenticatedPage
        .getByText(formattedTime.replace(/ AM| PM/, ''), {exact: false})
        .first()
        .click();

      await authenticatedPage.getByText('Change Expiration').click();

      // Expiration should remain as Never
      await expect(latestRow.locator('[data-label="Expires"]')).toHaveText(
        'Never',
      );
      await expect(
        authenticatedPage.getByText('Could not set expiration for tag latest'),
      ).toBeVisible();
    });
  },
);
