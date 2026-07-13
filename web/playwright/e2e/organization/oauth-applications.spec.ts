import {test, expect} from '../../fixtures';

test.describe('OAuth Applications', {tag: ['@organization']}, () => {
  test('OAuth app lifecycle: create, view, update, delete', async ({
    authenticatedPage: page,
    api,
  }) => {
    const org = await api.organization('oauth');

    // Navigate to OAuth Applications tab
    await page.goto(`/organization/${org.name}?tab=OAuthApplications`);

    // Should show empty state
    await expect(
      page.getByText("doesn't have any OAuth applications"),
    ).toBeVisible();

    // Create via empty state button
    await page.getByText('Create new application').click();
    await expect(page.getByTestId('create-oauth-modal')).toBeVisible();

    // Submit should be disabled without name
    await expect(page.getByTestId('create-oauth-submit')).toBeDisabled();

    // Fill form and create
    await page.getByTestId('application-name-input').fill('test-oauth-app');
    await page.getByTestId('homepage-url-input').fill('https://example.com');
    await page.getByTestId('description-input').fill('Test application');
    await expect(page.getByTestId('create-oauth-submit')).toBeEnabled();
    await page.getByTestId('create-oauth-submit').click();

    // Should show success and app in list
    await expect(
      page.getByText('Successfully created application').first(),
    ).toBeVisible();
    // Verify app appears in table
    const appButton = page
      .getByTestId('oauth-applications-table')
      .getByRole('button', {name: 'test-oauth-app'});
    await expect(appButton).toBeVisible();

    // Click app to open the management modal
    await appButton.click();
    await expect(
      page.getByText('Manage OAuth Application: test-oauth-app'),
    ).toBeVisible();

    // Verify all tabs exist
    await expect(
      page.getByRole('tab', {name: 'Settings', exact: true}),
    ).toBeVisible();
    await expect(
      page.getByRole('tab', {name: 'OAuth Information'}),
    ).toBeVisible();
    await expect(
      page.getByRole('tab', {name: 'API Access Tokens'}),
    ).toBeVisible();

    // Verify settings values
    await expect(page.getByTestId('application-name-input')).toHaveValue(
      'test-oauth-app',
    );

    // Switch to OAuth Information tab
    await page.getByRole('tab', {name: 'OAuth Information'}).click();
    await expect(page.getByText('Client ID:')).toBeVisible();
    await expect(page.getByText('Client Secret:')).toBeVisible();

    // Close modal by clicking the X button
    await page
      .getByTestId('manage-oauth-modal')
      .getByRole('button', {name: 'Close'})
      .click();
    await page.getByTestId('oauth-application-actions').first().click();
    await page.getByRole('menuitem', {name: 'Delete'}).click();

    // Confirm deletion
    await page.getByTestId('test-oauth-app-del-btn').click();
    await expect(
      page.getByText('Successfully deleted oauth application').first(),
    ).toBeVisible();
  });

  test(
    'API access token lifecycle: generate, copy, refresh, and revoke',
    {tag: '@PROJQUAY-9857'},
    async ({authenticatedPage: page, api}) => {
      const org = await api.organization('oauth-token-ui');
      const app = await api.oauthApplication(org.name, 'token-ui-app');
      const tokenName = 'ui-token';

      await page
        .context()
        .grantPermissions(['clipboard-read', 'clipboard-write']);
      await page.goto(`/organization/${org.name}?tab=OAuthApplications`);

      const openApplication = async (): Promise<void> => {
        await page
          .getByTestId('oauth-applications-table')
          .getByRole('button', {name: app.name, exact: true})
          .click();
        await page.getByRole('tab', {name: 'API Access Tokens'}).click();
      };

      await openApplication();
      await expect(page.getByText('No API access tokens')).toBeVisible();
      await page.getByTestId('generate-new-api-token-button').click();
      await page.getByTestId('api-token-name-input').fill(tokenName);
      await page.getByTestId('api-token-scope-repo:read').click();
      await page.getByTestId('generate-api-token-submit').click();
      await page.getByRole('button', {name: 'Authorize Application'}).click();

      const tokenDisplayModal = page.getByTestId('token-display-modal');
      await expect(tokenDisplayModal).toBeVisible();
      const secretControl = tokenDisplayModal.getByTestId(
        'generated-token-secret',
      );
      const secretInput = secretControl.getByLabel('Copyable input');
      await expect(secretInput).not.toHaveValue('');
      const generatedSecret = await secretInput.inputValue();

      await secretControl.getByLabel('Copy to clipboard').click();
      const clipboardSecret = await page.evaluate(() =>
        navigator.clipboard.readText(),
      );
      expect(clipboardSecret).toBe(generatedSecret);

      await tokenDisplayModal.getByTestId('token-display-done').click();
      let tokenRow = page
        .getByTestId('api-access-tokens-table')
        .getByRole('row')
        .filter({hasText: tokenName});
      await expect(tokenRow).toBeVisible();

      await page.reload();
      await openApplication();
      tokenRow = page
        .getByTestId('api-access-tokens-table')
        .getByRole('row')
        .filter({hasText: tokenName});
      await expect(tokenRow).toBeVisible();

      await tokenRow
        .getByRole('button', {name: `Actions for ${tokenName}`})
        .click();
      await page.getByRole('menuitem', {name: 'Revoke'}).click();
      await expect(page.getByTestId('revoke-api-token-modal')).toBeVisible();
      await page.getByTestId('revoke-api-token-confirm').click();

      await expect(tokenRow).not.toBeVisible();
      await expect(page.getByText('No API access tokens')).toBeVisible();
    },
  );

  test(
    'non-admin users cannot see OAuth Applications tab',
    {tag: '@superuser'},
    async ({authenticatedPage: page, superuserApi}) => {
      // Create org as superuser so testuser is NOT an admin
      const org = await superuserApi.organization('noadmin');

      await page.goto(`/organization/${org.name}`);

      // OAuth Applications tab should not be visible
      await expect(page.getByText('OAuth Applications')).not.toBeVisible();
    },
  );

  test('bulk select and delete apps with the same name', async ({
    authenticatedPage: page,
    api,
  }) => {
    const org = await api.organization('bulkdel');

    // Create three apps with the same name via API
    await api.oauthApplication(org.name, 'samename');
    await api.oauthApplication(org.name, 'samename');
    await api.oauthApplication(org.name, 'samename');

    await page.goto(`/organization/${org.name}?tab=OAuthApplications`);

    const table = page.getByTestId('oauth-applications-table');
    await expect(table).toBeVisible();

    // All three should be visible
    await expect(table.locator('tbody tr')).toHaveCount(3);

    // Open dropdown and select all (scope to OAuth tabpanel to avoid ambiguity with other tab toolbars)
    await page
      .getByRole('tabpanel', {name: 'OAuth Applications'})
      .locator('#toolbar-dropdown-checkbox')
      .click();
    await page.getByTestId('select-all-items-action').click();

    // All row checkboxes should be checked
    await expect(
      page.getByRole('checkbox', {name: 'Select row 0'}),
    ).toBeChecked();
    await expect(
      page.getByRole('checkbox', {name: 'Select row 1'}),
    ).toBeChecked();
    await expect(
      page.getByRole('checkbox', {name: 'Select row 2'}),
    ).toBeChecked();

    // Click bulk delete
    await page.getByTestId('default-perm-bulk-delete-icon').click();
    await expect(page.getByTestId('bulk-delete-modal')).toBeVisible();

    // Type confirmation and delete
    await page.getByTestId('delete-confirmation-input').fill('confirm');
    await page.getByTestId('bulk-delete-confirm-btn').click();

    // Verify success and empty state
    await expect(
      page.getByText('Successfully deleted OAuth applications').first(),
    ).toBeVisible();
    await expect(
      page.getByText("doesn't have any OAuth applications"),
    ).toBeVisible();

    // Verify all three are gone via API
    const remaining = await api.raw.getOAuthApplications(org.name);
    expect(remaining).toHaveLength(0);
  });

  test('reset client secret with confirmation', async ({
    authenticatedPage: page,
    api,
  }) => {
    const org = await api.organization('secretreset');
    const app = await api.oauthApplication(org.name, 'secretapp');

    await page.goto(`/organization/${org.name}?tab=OAuthApplications`);
    await expect(page.getByText(app.name)).toBeVisible();

    // Open the management modal and go to OAuth Information
    await page.getByText(app.name).click();
    await page.getByText('OAuth Information').click();

    // Note the current secret
    const secretBefore = app.clientSecret;

    // Click reset
    await page.getByTestId('reset-client-secret-button').click();
    await page.getByTestId('confirm-reset-secret').click();

    await expect(
      page.getByText('Client secret reset successfully').first(),
    ).toBeVisible();

    // Verify secret changed via API
    const apps = await api.raw.getOAuthApplications(org.name);
    const updatedApp = apps.find((a) => a.client_id === app.clientId);
    expect(updatedApp).toBeDefined();
    if (secretBefore) {
      expect(updatedApp?.client_secret).not.toBe(secretBefore);
    }
  });
});
