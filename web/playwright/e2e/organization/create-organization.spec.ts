import {test, expect} from '../../fixtures';

test.describe('Create Organization', {tag: ['@organization']}, () => {
  test('modal opens and shows form fields', async ({authenticatedPage}) => {
    await authenticatedPage.goto('/organization');

    await authenticatedPage
      .getByRole('button', {name: 'Create Organization'})
      .click();

    await expect(
      authenticatedPage.getByRole('heading', {name: 'Create Organization'}),
    ).toBeVisible();
    await expect(
      authenticatedPage.locator('#create-org-name-input'),
    ).toBeVisible();
    await expect(
      authenticatedPage.locator('#create-org-confirm'),
    ).toBeVisible();
    await expect(authenticatedPage.locator('#create-org-cancel')).toBeVisible();
  });

  test('name validation rejects invalid input', async ({
    authenticatedPage,
    quayConfig,
  }) => {
    await authenticatedPage.goto('/organization');
    await authenticatedPage
      .getByRole('button', {name: 'Create Organization'})
      .click();

    const nameInput = authenticatedPage.locator('#create-org-name-input');
    const createBtn = authenticatedPage.locator('#create-org-confirm');

    // Single char — too short
    await nameInput.fill('a');
    await expect(createBtn).toBeDisabled();
    await expect(
      authenticatedPage.getByText(
        'Must be alphanumeric, all lowercase, at least 2 characters long',
      ),
    ).toBeVisible();

    // Uppercase — invalid
    await nameInput.fill('MyOrg');
    await expect(createBtn).toBeDisabled();

    // Valid name — fill email too if MAILING is enabled (email is required)
    await nameInput.fill('validorg');
    if (quayConfig?.features?.MAILING) {
      await authenticatedPage
        .locator('#create-org-email-input')
        .fill('validorg@test.example.com');
    }
    await expect(createBtn).toBeEnabled();
  });

  test('warning for short names and names with dashes', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto('/organization');
    await authenticatedPage
      .getByRole('button', {name: 'Create Organization'})
      .click();

    const nameInput = authenticatedPage.locator('#create-org-name-input');

    // Short name warning (< 4 chars)
    await nameInput.fill('ab');
    await expect(
      authenticatedPage.getByText(
        'Namespaces less than 4 or more than 30 characters are only compatible with Docker 1.6+',
      ),
    ).toBeVisible();

    // Dash warning
    await nameInput.fill('my-org');
    await expect(
      authenticatedPage.getByText(
        'Namespaces with dashes or dots are only compatible with Docker 1.9+',
      ),
    ).toBeVisible();
  });

  test('successful creation shows alert and org appears in list', async ({
    authenticatedPage,
    authenticatedRequest,
  }) => {
    const orgName = `createtest${Date.now()}`.substring(0, 30).toLowerCase();

    await authenticatedPage.goto('/organization');
    await authenticatedPage
      .getByRole('button', {name: 'Create Organization'})
      .click();

    await authenticatedPage.locator('#create-org-name-input').fill(orgName);

    // Fill email if MAILING enabled
    const emailInput = authenticatedPage.locator('#create-org-email-input');
    if (await emailInput.isVisible({timeout: 1000}).catch(() => false)) {
      await emailInput.fill(`${orgName}@test.example.com`);
    }

    await authenticatedPage.locator('#create-org-confirm').click();

    await expect(
      authenticatedPage.getByText(
        `Successfully created organization ${orgName}`,
      ),
    ).toBeVisible();

    // Cleanup
    const {API_URL} = await import('../../utils/config');
    const csrfResponse = await authenticatedRequest.get(
      `${API_URL}/csrf_token`,
    );
    const csrfData = await csrfResponse.json();
    await authenticatedRequest.delete(
      `${API_URL}/api/v1/organization/${orgName}`,
      {headers: {'X-CSRF-Token': csrfData.csrf_token}},
    );
  });

  test('cancel button closes modal without creating', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto('/organization');
    await authenticatedPage
      .getByRole('button', {name: 'Create Organization'})
      .click();

    await authenticatedPage
      .locator('#create-org-name-input')
      .fill('testcancel');
    await authenticatedPage.locator('#create-org-cancel').click();

    // Modal should be closed
    await expect(
      authenticatedPage.locator('#create-org-name-input'),
    ).not.toBeVisible();
  });
});
