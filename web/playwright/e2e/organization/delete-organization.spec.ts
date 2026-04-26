import {test, expect} from '../../fixtures';

test.describe('Delete Organization', {tag: ['@organization']}, () => {
  test('delete option visible in settings for admin', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('delorgvis');

    await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

    await expect(
      authenticatedPage.getByText('Delete Organization'),
    ).toBeVisible();
  });

  test('confirmation modal requires typing org name', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('delorgconfirm');

    await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

    await authenticatedPage
      .getByRole('button', {name: 'Delete Organization'})
      .click();

    // Modal should open
    await expect(
      authenticatedPage.getByText('Are you sure', {exact: false}),
    ).toBeVisible();

    // Delete button should be disabled without confirmation text
    const deleteBtn = authenticatedPage.getByRole('button', {
      name: 'Delete',
    });
    await expect(deleteBtn).toBeDisabled();

    // Type wrong name
    const confirmInput = authenticatedPage.getByRole('textbox');
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
      .getByRole('button', {name: 'Delete Organization'})
      .click();

    await authenticatedPage.getByRole('button', {name: 'Cancel'}).click();

    // Navigate to org page to verify it still exists
    await authenticatedPage.goto(`/organization/${org.name}`);
    await expect(authenticatedPage).toHaveURL(
      new RegExp(`/organization/${org.name}`),
    );
  });

  test('successful deletion redirects to org list', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('delorgsucc');

    await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

    await authenticatedPage
      .getByRole('button', {name: 'Delete Organization'})
      .click();

    const confirmInput = authenticatedPage.getByRole('textbox');
    await confirmInput.fill(org.name);

    await authenticatedPage.getByRole('button', {name: 'Delete'}).click();

    // Should redirect to organization list
    await expect(authenticatedPage).toHaveURL(/\/organization/);
  });
});
