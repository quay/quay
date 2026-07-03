import {test, expect} from '../../fixtures';

test.describe('Delete organization', {tag: ['@organization']}, () => {
  test('delete option visible in settings for admin', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('delorgvis');

    await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

    await expect(
      authenticatedPage.getByText('Delete organization'),
    ).toBeVisible();
  });

  test('confirmation modal requires typing org name', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('delorgconfirm');

    await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

    await authenticatedPage
      .getByRole('button', {name: 'Delete organization'})
      .click();

    // Modal should open with confirmation instructions
    await expect(
      authenticatedPage.getByText('You must type', {exact: false}),
    ).toBeVisible();

    // Delete button should be disabled without confirmation text
    const deleteBtn = authenticatedPage.getByTestId('delete-account-confirm');
    await expect(deleteBtn).toBeDisabled();

    // Type wrong name
    const confirmInput = authenticatedPage.locator(
      '#delete-confirmation-input',
    );
    await confirmInput.fill('wrongname');
    await expect(deleteBtn).toBeDisabled();

    // Type correct name
    await confirmInput.fill(org.name);
    await expect(deleteBtn).toBeEnabled();
  });

  test('cancel closes modal without deleting', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('delorgcancel');

    await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

    await authenticatedPage
      .getByRole('button', {name: 'Delete organization'})
      .click();

    await authenticatedPage.getByRole('button', {name: 'Cancel'}).click();

    // Modal should be closed
    await expect(
      authenticatedPage.getByTestId('delete-account-modal'),
    ).not.toBeVisible();

    // Org page should still be accessible
    await authenticatedPage.goto(`/organization/${org.name}`);
    await expect(authenticatedPage).toHaveURL(
      new RegExp(`/organization/${org.name}$`),
    );
  });

  test('successful deletion redirects to org list', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('delorgsucc');

    await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

    await authenticatedPage
      .getByRole('button', {name: 'Delete organization'})
      .click();

    const confirmInput = authenticatedPage.locator(
      '#delete-confirmation-input',
    );
    await confirmInput.fill(org.name);

    await authenticatedPage.getByTestId('delete-account-confirm').click();

    // Should redirect to root/organization list, not stay on deleted org page
    await expect(authenticatedPage).toHaveURL(/\/organization$/);
  });

  test.describe(
    'with organization mirroring',
    {tag: ['@feature:ORG_MIRROR']},
    () => {
      test('successful deletion redirects when org mirror is configured', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization('delorgmirr');
        const robot = await api.robot(org.name, 'mirrorbot');
        const syncStartDate = new Date();
        syncStartDate.setMinutes(syncStartDate.getMinutes() + 5);

        await api.raw.createOrgMirrorConfig(org.name, {
          external_registry_type: 'quay',
          external_registry_url: 'https://quay.io',
          external_namespace: 'projectquay',
          robot_username: robot.fullName,
          visibility: 'private',
          sync_interval: 3600,
          sync_start_date: syncStartDate
            .toISOString()
            .replace(/\.\d{3}Z$/, 'Z'),
        });

        await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

        await authenticatedPage
          .getByRole('button', {name: 'Delete organization'})
          .click();

        await authenticatedPage
          .locator('#delete-confirmation-input')
          .fill(org.name);
        await authenticatedPage.getByTestId('delete-account-confirm').click();

        await expect(authenticatedPage).toHaveURL(/\/organization$/);
      });
    },
  );
});
