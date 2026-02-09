import {test, expect, uniqueName} from '../../fixtures';

test.describe(
  'Service Keys',
  {tag: ['@superuser', '@feature:SUPERUSERS_FULL_ACCESS']},
  () => {
    test('non-superuser is redirected to organization page', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto('/service-keys');
      await expect(authenticatedPage).toHaveURL(/\/organization/);
    });

    test('superuser can create, view, and manage service keys', async ({
      superuserPage,
    }) => {
      await superuserPage.goto('/service-keys');

      // Verify page loads correctly
      await expect(
        superuserPage.getByRole('heading', {name: 'Service Keys'}),
      ).toBeVisible();
      await expect(
        superuserPage.getByText(
          'Service keys provide a recognized means of authentication',
        ),
      ).toBeVisible();
      await expect(
        superuserPage.getByRole('button', {name: 'Create Preshareable Key'}),
      ).toBeEnabled();

      // Verify table columns
      await expect(
        superuserPage.getByRole('columnheader', {name: 'Name', exact: true}),
      ).toBeVisible();
      await expect(
        superuserPage.getByRole('columnheader', {name: 'Service Name'}),
      ).toBeVisible();
      await expect(
        superuserPage.getByRole('columnheader', {name: 'Created'}),
      ).toBeVisible();
      await expect(
        superuserPage.getByRole('columnheader', {name: 'Expires'}),
      ).toBeVisible();
      await expect(
        superuserPage.getByRole('columnheader', {name: 'Approval Status'}),
      ).toBeVisible();

      // Create a new service key via UI
      await superuserPage
        .getByRole('button', {name: 'Create Preshareable Key'})
        .click();
      await expect(
        superuserPage.getByTestId('create-service-key-modal'),
      ).toBeVisible();
      await expect(
        superuserPage.getByRole('heading', {
          name: 'Create Preshareable Service Key',
        }),
      ).toBeVisible();

      const keyName = uniqueName('testkey');
      const serviceName = `svc_${Date.now()}`;
      // Future date for expiration
      const futureDate = new Date();
      futureDate.setFullYear(futureDate.getFullYear() + 1);
      const expirationValue = futureDate.toISOString().slice(0, 16); // YYYY-MM-DDTHH:MM

      // Fill out the create form
      await superuserPage.locator('#key-name').fill(keyName);
      await superuserPage.locator('#service-name').fill(serviceName);
      await superuserPage.locator('#expiration').fill(expirationValue);

      // Submit the form
      await superuserPage.getByTestId('create-key-submit').click();

      // Modal should close and new key should appear in table
      await expect(
        superuserPage.getByTestId('create-service-key-modal'),
      ).not.toBeVisible();
      await expect(superuserPage.getByText(keyName)).toBeVisible();
      await expect(superuserPage.getByText(serviceName)).toBeVisible();

      // Test search filtering
      await superuserPage.getByTestId('service-keys-search').fill(keyName);
      await expect(superuserPage.getByText(keyName)).toBeVisible();
      // Clear search
      await superuserPage.getByTestId('service-keys-search').clear();

      // Find the row with our key - use the expand link to get the kid
      const keyRow = superuserPage.locator('tbody', {
        has: superuserPage.getByText(keyName),
      });

      // Expand key details - click the name link
      const expandLink = keyRow.locator(`[data-testid^="expand-"]`);
      await expandLink.click();

      // Verify expanded details are visible (scoped to this key's tbody)
      await expect(keyRow.getByText('Full Key ID')).toBeVisible();

      // Collapse the details
      await expandLink.click();

      // Open action menu and change expiration
      const actionsToggle = keyRow.locator(`[data-testid$="-actions-toggle"]`);
      await actionsToggle.click();
      await superuserPage
        .getByRole('menuitem', {name: 'Change Expiration Time'})
        .click();

      // Change expiration modal
      await expect(
        superuserPage.getByTestId('change-expiration-modal'),
      ).toBeVisible();
      const newFutureDate = new Date();
      newFutureDate.setFullYear(newFutureDate.getFullYear() + 2);
      await superuserPage
        .getByTestId('expiration-date-input')
        .fill(newFutureDate.toISOString().slice(0, 16));
      await superuserPage.getByTestId('save-expiration-button').click();
      await expect(
        superuserPage.getByTestId('change-expiration-modal'),
      ).not.toBeVisible();

      // Open action menu and set friendly name
      await actionsToggle.click();
      await superuserPage
        .getByRole('menuitem', {name: 'Set Friendly Name'})
        .click();

      // Set name modal
      await expect(superuserPage.getByTestId('set-name-modal')).toBeVisible();
      const newName = `${keyName}-updated`;
      await superuserPage.getByTestId('friendly-name-input').fill(newName);
      await superuserPage.getByTestId('save-name-button').click();
      await expect(
        superuserPage.getByTestId('set-name-modal'),
      ).not.toBeVisible();

      // Verify name was updated
      await expect(superuserPage.getByText(newName)).toBeVisible();

      // Delete the key
      await actionsToggle.click();
      await superuserPage.getByRole('menuitem', {name: 'Delete Key'}).click();

      // Delete confirmation modal
      await expect(
        superuserPage.getByTestId('delete-service-key-modal'),
      ).toBeVisible();
      await expect(
        superuserPage.getByText('Are you sure you want to delete'),
      ).toBeVisible();
      await superuserPage.getByTestId('confirm-delete-button').click();

      // Modal closes and key is removed
      await expect(
        superuserPage.getByTestId('delete-service-key-modal'),
      ).not.toBeVisible();
      await expect(superuserPage.getByText(newName)).not.toBeVisible();
    });

    test('shows error state when create fails', async ({superuserPage}) => {
      await superuserPage.route('**/api/v1/superuser/keys', async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 400,
            contentType: 'application/json',
            body: JSON.stringify({
              error_message: 'Service already exists',
              error_type: 'invalid_request',
            }),
          });
        } else {
          await route.continue();
        }
      });

      await superuserPage.goto('/service-keys');
      await expect(
        superuserPage.getByRole('heading', {name: 'Service Keys'}),
      ).toBeVisible();

      // Open create modal
      await superuserPage
        .getByRole('button', {name: 'Create Preshareable Key'})
        .click();
      await expect(
        superuserPage.getByTestId('create-service-key-modal'),
      ).toBeVisible();

      // Fill required fields
      await superuserPage.locator('#key-name').fill('Test Key');
      await superuserPage.locator('#service-name').fill('test_service');
      const futureDate = new Date();
      futureDate.setFullYear(futureDate.getFullYear() + 1);
      await superuserPage
        .locator('#expiration')
        .fill(futureDate.toISOString().slice(0, 16));

      // Submit - should fail
      await superuserPage.getByTestId('create-key-submit').click();

      // Error should be displayed, modal should stay open
      await expect(
        superuserPage.getByTestId('create-service-key-modal'),
      ).toBeVisible();
      // Look for error message in the modal
      await expect(
        superuserPage.getByText(/Service already exists|Error/i),
      ).toBeVisible();
    });

    test('read-only superuser has limited access', async ({
      readonlyPage,
      superuserApi,
    }) => {
      // Create a service key via API for there to be data
      const serviceName = `svc_${Date.now()}`;
      const key = await superuserApi.serviceKey(serviceName, 'Test Key');

      await readonlyPage.goto('/service-keys');

      // Verify page loads (read-only superuser can access)
      await expect(readonlyPage).toHaveURL(/\/service-keys/);
      await expect(
        readonlyPage.getByRole('heading', {name: 'Service Keys'}),
      ).toBeVisible();

      // Verify the created key is visible
      await expect(readonlyPage.getByText('Test Key')).toBeVisible();

      // Create button should be disabled
      await expect(
        readonlyPage.getByRole('button', {name: 'Create Preshareable Key'}),
      ).toBeDisabled();

      // Open row action menu - all items should be aria-disabled
      const keyRow = readonlyPage.locator('tr', {
        has: readonlyPage.getByText('Test Key'),
      });
      const actionsToggle = keyRow.locator(`[data-testid$="-actions-toggle"]`);
      await actionsToggle.click();

      await expect(
        readonlyPage.getByRole('menuitem', {name: 'Set Friendly Name'}),
      ).toHaveAttribute('aria-disabled', 'true');
      await expect(
        readonlyPage.getByRole('menuitem', {name: 'Change Expiration Time'}),
      ).toHaveAttribute('aria-disabled', 'true');
      await expect(
        readonlyPage.getByRole('menuitem', {name: 'Delete Key'}),
      ).toHaveAttribute('aria-disabled', 'true');

      // Close the action menu
      await readonlyPage.keyboard.press('Escape');

      // Select the key and verify bulk delete is disabled
      await keyRow.getByTestId(`select-${key.kid}`).locator('input').click();

      // Click Actions button
      await readonlyPage.getByRole('button', {name: 'Actions'}).click();

      // Delete Keys option should be disabled
      await expect(
        readonlyPage
          .getByTestId('bulk-delete-keys')
          .locator('button, [role="menuitem"]'),
      ).toHaveAttribute('aria-disabled', 'true');
    });

    test('superuser can perform bulk operations', async ({
      superuserPage,
      superuserApi,
    }) => {
      // Create 2 service keys via API
      const svc1 = `svc1_${Date.now()}`;
      const svc2 = `svc2_${Date.now()}`;
      const key1 = await superuserApi.serviceKey(svc1, 'Bulk Key 1');
      const key2 = await superuserApi.serviceKey(svc2, 'Bulk Key 2');

      await superuserPage.goto('/service-keys');

      // Verify both keys are visible
      await expect(superuserPage.getByText('Bulk Key 1')).toBeVisible();
      await expect(superuserPage.getByText('Bulk Key 2')).toBeVisible();

      // Select both keys using individual checkboxes
      await superuserPage
        .getByTestId(`select-${key1.kid}`)
        .locator('input')
        .click();
      await superuserPage
        .getByTestId(`select-${key2.kid}`)
        .locator('input')
        .click();

      // Click Actions button (appears when items are selected)
      await superuserPage.getByRole('button', {name: 'Actions'}).click();

      // Click Delete Keys
      await superuserPage.getByTestId('bulk-delete-keys').click();

      // Bulk delete modal should appear
      await expect(
        superuserPage.getByTestId('bulk-delete-modal'),
      ).toBeVisible();
      await expect(superuserPage.getByText('2 service keys')).toBeVisible();

      // Confirm bulk delete
      await superuserPage.getByTestId('confirm-bulk-delete').click();

      // Modal closes and both keys should be removed
      await expect(
        superuserPage.getByTestId('bulk-delete-modal'),
      ).not.toBeVisible();
      await expect(superuserPage.getByText('Bulk Key 1')).not.toBeVisible();
      await expect(superuserPage.getByText('Bulk Key 2')).not.toBeVisible();
    });
  },
);
