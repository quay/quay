import {test, expect, uniqueName} from '../../fixtures';

test.describe(
  'Superuser Messages',
  {tag: ['@superuser', '@feature:SUPERUSERS_FULL_ACCESS']},
  () => {
    test('non-superuser is redirected to organization page', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto('/messages');
      await expect(authenticatedPage).toHaveURL(/\/organization/);
    });

    test('superuser can create, view, and delete messages', async ({
      superuserPage,
    }) => {
      await superuserPage.goto('/messages');

      // Verify page loads correctly (superuser access implicit)
      await expect(
        superuserPage.getByRole('heading', {name: 'Messages', exact: true}),
      ).toBeVisible();
      await expect(
        superuserPage.getByRole('button', {name: 'Create Message'}),
      ).toBeEnabled();

      // Create message via UI
      await superuserPage.getByRole('button', {name: 'Create Message'}).click();
      await expect(superuserPage.getByRole('dialog')).toBeVisible();

      const messageContent = `Test message ${uniqueName('msg')}`;
      await superuserPage
        .locator('textarea[placeholder="Enter your message here..."]')
        .fill(messageContent);
      await superuserPage.locator('#severity').selectOption('warning');
      await superuserPage
        .getByRole('dialog')
        .getByRole('button', {name: 'Create Message'})
        .click();

      // Modal closes, message appears in table
      await expect(superuserPage.getByRole('dialog')).not.toBeVisible();
      // Check for message in the table specifically (it also appears in banner)
      await expect(
        superuserPage.locator('tbody').getByText(messageContent),
      ).toBeVisible();

      // Delete the message
      // Find the row with our message and click its action toggle
      const row = superuserPage.locator('tr', {
        has: superuserPage.getByText(messageContent),
      });
      await row.locator('[data-testid$="-actions-toggle"]').click();
      await superuserPage.getByRole('menuitem', {name: 'Delete'}).click();

      // Confirm deletion
      await expect(superuserPage.getByRole('dialog')).toBeVisible();
      await superuserPage
        .getByRole('dialog')
        .getByRole('button', {name: 'Delete'})
        .click();
      await expect(superuserPage.getByRole('dialog')).not.toBeVisible();

      // Message should be gone from the table
      await expect(
        superuserPage.locator('tbody').getByText(messageContent),
      ).not.toBeVisible();
    });

    test('shows error state when messages fail to load', async ({
      superuserPage,
    }) => {
      await superuserPage.route('**/api/v1/messages', async (route) => {
        await route.fulfill({
          status: 500,
          body: JSON.stringify({error: 'Internal server error'}),
        });
      });

      await superuserPage.goto('/messages');
      await expect(
        superuserPage.getByText('Error Loading Messages'),
      ).toBeVisible();
    });

    test('shows loading spinner while fetching messages', async ({
      superuserPage,
    }) => {
      await superuserPage.route('**/api/v1/messages', async (route) => {
        await new Promise((r) => setTimeout(r, 2000));
        await route.fulfill({
          status: 200,
          body: JSON.stringify({messages: []}),
        });
      });

      await superuserPage.goto('/messages');
      await expect(superuserPage.locator('.pf-v5-c-spinner')).toBeVisible();
    });

    // Read-only superuser tests use the existing readonlyPage fixture
    // The readonly user is configured as a global_readonly_super_user in config.yaml

    test('read-only superuser can access messages page', async ({
      readonlyPage,
      superuserApi,
    }) => {
      // Create a message so there's something to see (auto-cleanup)
      await superuserApi.message('Test message for readonly view', 'info');

      await readonlyPage.goto('/messages');
      await expect(readonlyPage).toHaveURL(/\/messages/);
      await expect(
        readonlyPage.getByRole('heading', {name: 'Messages', exact: true}),
      ).toBeVisible();
      // Verify message appears in the table body (PatternFly table)
      await expect(readonlyPage.locator('tbody')).toBeVisible();
      await expect(
        readonlyPage
          .locator('tbody')
          .getByText('Test message for readonly view'),
      ).toBeVisible();
      // Message is auto-cleaned by superuserApi fixture
    });

    test('read-only superuser sees disabled create and delete actions', async ({
      readonlyPage,
      superuserApi,
    }) => {
      // Create a message to test delete action (auto-cleanup)
      const msg = await superuserApi.message(
        'Test message for readonly permissions',
        'info',
      );

      await readonlyPage.goto('/messages');
      await expect(readonlyPage).toHaveURL(/\/messages/);

      // Create Message button should be disabled
      await expect(
        readonlyPage.getByRole('button', {name: 'Create Message'}),
      ).toBeDisabled();

      // Click action menu - delete option should be aria-disabled
      const row = readonlyPage.locator('tr', {
        has: readonlyPage.getByText(msg.content),
      });
      await row.locator('[data-testid$="-actions-toggle"]').click();
      await expect(
        readonlyPage.getByRole('menuitem', {name: 'Delete'}),
      ).toHaveAttribute('aria-disabled', 'true');
      // Message is auto-cleaned by superuserApi fixture
    });
  },
);
