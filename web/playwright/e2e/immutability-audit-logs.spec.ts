import {test, expect} from '../fixtures';
import {pushImage} from '../utils/container';
import {TEST_USERS} from '../global-setup';

test.describe(
  'Immutability Audit Logs',
  {tag: ['@logs', '@container', '@feature:IMMUTABLE_TAGS']},
  () => {
    test('logs retroactive immutability changes in usage logs', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('immaudit');
      const repo = await api.repository(org.name, 'immauditrepo');

      // Push an image with a tag that will match the policy
      await pushImage(
        org.name,
        repo.name,
        'v1.0.0',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Create immutability policy matching v* tags
      // This retroactively marks the existing v1.0.0 tag as immutable
      await api.orgImmutabilityPolicy(org.name, '^v.*$', true);

      // Navigate to Usage Logs tab
      await authenticatedPage.goto(`/organization/${org.name}?tab=Logs`);

      // Wait for table to load
      await expect(
        authenticatedPage.getByTestId('usage-logs-table'),
      ).toBeVisible();

      // Filter by "immutable" to find our log entries
      await authenticatedPage
        .getByPlaceholder('Filter logs')
        .fill('set as immutable by policy');

      await authenticatedPage.waitForTimeout(500);

      // Verify the retroactive batch log entry is visible
      await expect(
        authenticatedPage
          .getByTestId('usage-logs-table')
          .getByText('existing tag matching'),
      ).toBeVisible();
    });

    test('logs tag made immutable on push in usage logs', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('immaudit2');
      const repo = await api.repository(org.name, 'immauditrepo2');

      // Create immutability policy FIRST
      await api.orgImmutabilityPolicy(org.name, '^v.*$', true);

      // Push an image with a matching tag — should be auto-immutable
      await pushImage(
        org.name,
        repo.name,
        'v1.0.0',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Navigate to Usage Logs tab
      await authenticatedPage.goto(`/organization/${org.name}?tab=Logs`);

      // Wait for table to load
      await expect(
        authenticatedPage.getByTestId('usage-logs-table'),
      ).toBeVisible();

      // Filter to find our log entry
      await authenticatedPage
        .getByPlaceholder('Filter logs')
        .fill('automatically set as immutable');

      await authenticatedPage.waitForTimeout(500);

      // Verify the per-tag log entry is visible
      await expect(
        authenticatedPage
          .getByTestId('usage-logs-table')
          .getByText('automatically set as immutable by policy'),
      ).toBeVisible();
    });
  },
);
