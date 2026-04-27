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
});
