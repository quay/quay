import {test, expect} from '../../fixtures';

test.describe(
  'Organization Time Machine',
  {tag: ['@organization', '@feature:CHANGE_TAG_EXPIRATION']},
  () => {
    test('displays time machine dropdown with configured expiration options', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('tmorg');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

      // Verify Time machine form group is visible
      await expect(
        authenticatedPage.getByText('Time machine', {exact: true}),
      ).toBeVisible();

      // Verify the dropdown is present
      const picker = authenticatedPage.getByTestId('tag-expiration-picker');
      await expect(picker).toBeVisible();

      // Verify helper text explains the feature
      await expect(
        authenticatedPage.getByText(
          'The amount of time, after a tag is deleted',
        ),
      ).toBeVisible();
    });

    test('changes time machine expiration and saves', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('tmchangeorg');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

      const picker = authenticatedPage.getByTestId('tag-expiration-picker');
      await expect(picker).toBeVisible();

      // Get the current value
      const currentValue = await picker.inputValue();

      // Get available options from the select
      const options = picker.locator('option');
      const optionCount = await options.count();
      test.skip(optionCount < 2, 'Need at least 2 expiration options to test');

      // Pick a different option than the current one
      const firstOptionValue = await options.nth(0).getAttribute('value');
      const secondOptionValue = await options.nth(1).getAttribute('value');
      const newValue =
        currentValue === firstOptionValue
          ? secondOptionValue!
          : firstOptionValue!;

      await picker.selectOption(newValue);

      // Save settings
      const saveButton = authenticatedPage.getByTestId('settings-save-button');
      await expect(saveButton).toBeEnabled();
      await saveButton.click();

      // Verify success message
      await expect(
        authenticatedPage.getByText('Successfully updated settings').first(),
      ).toBeVisible();

      // Reload and verify the value persisted
      await authenticatedPage.reload();
      const updatedPicker = authenticatedPage.getByTestId(
        'tag-expiration-picker',
      );
      await expect(updatedPicker).toHaveValue(newValue);
    });
  },
);
