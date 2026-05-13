import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

test.describe(
  'Organization Auto-Prune Policies',
  {tag: ['@organization', '@feature:AUTO_PRUNE']},
  () => {
    test('updates and deletes org-level policy via settings UI', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgpruneupd');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByText('Auto-Prune Policies').click();

      // Create initial policy: By number of tags (25)
      await authenticatedPage
        .getByTestId('auto-prune-method')
        .selectOption('number_of_tags');

      const tagCountInput = authenticatedPage.locator(
        'input[aria-label="number of tags"]',
      );
      await tagCountInput.click({clickCount: 3});
      await tagCountInput.fill('25');
      await authenticatedPage.getByRole('button', {name: 'Save'}).click();

      await expect(
        authenticatedPage.getByText('Successfully created auto-prune policy'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Successfully created auto-prune policy'),
      ).not.toBeVisible({timeout: 10000});

      // Update to "By age of tags" (2 weeks)
      await authenticatedPage
        .getByTestId('auto-prune-method')
        .selectOption('creation_date');
      await authenticatedPage
        .locator('input[aria-label="tag creation date value"]')
        .fill('2');
      await authenticatedPage
        .locator('select[aria-label="tag creation date unit"]')
        .selectOption('w');
      await authenticatedPage.getByRole('button', {name: 'Save'}).click();

      await expect(
        authenticatedPage.getByText('Successfully updated auto-prune policy'),
      ).toBeVisible();
      await expect(
        authenticatedPage.locator(
          'input[aria-label="tag creation date value"]',
        ),
      ).toHaveValue('2');
      await expect(
        authenticatedPage.getByText('Successfully updated auto-prune policy'),
      ).not.toBeVisible({timeout: 10000});

      // Delete by setting to "None"
      await authenticatedPage
        .getByTestId('auto-prune-method')
        .selectOption('none');
      await authenticatedPage.getByRole('button', {name: 'Save'}).click();

      await expect(
        authenticatedPage.getByText('Successfully deleted auto-prune policy'),
      ).toBeVisible();
    });

    test('creates multiple policies at org level', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmultipol');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByText('Auto-Prune Policies').click();

      // First policy: By number of tags (25)
      const firstForm = authenticatedPage.locator('#autoprune-policy-form-0');
      await expect(firstForm.getByTestId('auto-prune-method')).toContainText(
        'None',
      );
      await firstForm
        .getByTestId('auto-prune-method')
        .selectOption('number_of_tags');

      const tagCountInput = firstForm.locator(
        'input[aria-label="number of tags"]',
      );
      await tagCountInput.fill('25');
      await firstForm.getByRole('button', {name: 'Save'}).click();

      await expect(
        authenticatedPage.getByText('Successfully created auto-prune policy'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Successfully created auto-prune policy'),
      ).not.toBeVisible({timeout: 10000});

      // Add second policy
      await authenticatedPage.getByRole('button', {name: 'Add Policy'}).click();
      await expect(
        authenticatedPage.locator('#autoprune-policy-form-1'),
      ).toBeVisible();

      // Second policy: By age of tags (2 weeks)
      const secondForm = authenticatedPage.locator('#autoprune-policy-form-1');
      await secondForm
        .getByTestId('auto-prune-method')
        .selectOption('creation_date');
      await secondForm
        .locator('input[aria-label="tag creation date value"]')
        .fill('2');
      await secondForm
        .locator('select[aria-label="tag creation date unit"]')
        .selectOption('w');
      await secondForm.getByRole('button', {name: 'Save'}).click();

      await expect(
        authenticatedPage.getByText('Successfully created auto-prune policy'),
      ).toBeVisible();

      await expect(
        authenticatedPage.locator('form[id^="autoprune-policy-form-"]'),
      ).toHaveCount(2);
    });

    test('creates multiple policies for user namespace', async ({
      authenticatedPage,
    }) => {
      const username = TEST_USERS.user.username;

      await authenticatedPage.goto(`/user/${username}?tab=Settings`);
      await authenticatedPage.getByTestId('Auto-Prune Policies').click();

      const firstForm = authenticatedPage.locator('#autoprune-policy-form-0');
      await expect(firstForm.getByTestId('auto-prune-method')).toBeVisible();
      await firstForm
        .getByTestId('auto-prune-method')
        .selectOption('number_of_tags');

      const tagCountInput = firstForm.locator(
        'input[aria-label="number of tags"]',
      );
      await tagCountInput.fill('10');
      await firstForm.getByRole('button', {name: 'Save'}).click();

      await expect(
        authenticatedPage.getByText('Successfully created auto-prune policy'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Successfully created auto-prune policy'),
      ).not.toBeVisible({timeout: 10000});

      await authenticatedPage.getByRole('button', {name: 'Add Policy'}).click();
      await expect(
        authenticatedPage.locator('#autoprune-policy-form-1'),
      ).toBeVisible();

      const secondForm = authenticatedPage.locator('#autoprune-policy-form-1');
      await secondForm
        .getByTestId('auto-prune-method')
        .selectOption('creation_date');
      await secondForm
        .locator('input[aria-label="tag creation date value"]')
        .fill('3');
      await secondForm
        .locator('select[aria-label="tag creation date unit"]')
        .selectOption('w');
      await secondForm.getByRole('button', {name: 'Save'}).click();

      await expect(
        authenticatedPage.getByText('Successfully created auto-prune policy'),
      ).toBeVisible();

      await expect(
        authenticatedPage.locator('form[id^="autoprune-policy-form-"]'),
      ).toHaveCount(2);

      // Cleanup: delete both policies so user namespace is clean for other tests
      for (let i = 0; i < 2; i++) {
        const form = authenticatedPage
          .locator('form[id^="autoprune-policy-form-"]')
          .first();
        await form.getByTestId('auto-prune-method').selectOption('none');
        await form.getByRole('button', {name: 'Save'}).click();
        await expect(
          authenticatedPage.getByText('Successfully deleted auto-prune policy'),
        ).toBeVisible();
        await expect(
          authenticatedPage.getByText('Successfully deleted auto-prune policy'),
        ).not.toBeVisible({timeout: 10000});
      }
    });
  },
);
