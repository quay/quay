import {test, expect, uniqueName} from '../../fixtures';
import {createRepository, deleteRepository} from '../../utils/api';
import {API_URL} from '../../utils/config';
import {TEST_USERS} from '../../global-setup';

test.describe('Repository Delete', {tag: ['@repository']}, () => {
  // Test data - unique per test run to avoid collisions
  const namespace = TEST_USERS.user.username;
  let repoName: string;

  test.beforeEach(async ({authenticatedRequest}) => {
    // Generate unique name for this test
    repoName = uniqueName('delrepo');

    // Create test repository in user's namespace via API
    await createRepository(authenticatedRequest, namespace, repoName);
  });

  test.afterEach(async ({authenticatedRequest}) => {
    // Cleanup: Delete repository if it still exists
    try {
      await deleteRepository(authenticatedRequest, namespace, repoName);
    } catch {
      // Repository already deleted by test or never created
    }
  });

  test('deletes repository via settings page and verifies removal', async ({
    authenticatedPage,
    authenticatedRequest,
  }) => {
    // Navigate to repository settings
    await authenticatedPage.goto(
      `/repository/${namespace}/${repoName}?tab=settings`,
    );

    // Click on "Delete Repository" tab in settings sidebar
    await authenticatedPage
      .getByTestId('settings-tab-deleterepository')
      .click();

    // Verify warning message is displayed
    await expect(
      authenticatedPage.getByText(
        'Deleting a repository cannot be undone. Here be dragons!',
      ),
    ).toBeVisible();

    // Click the delete button to open confirmation modal
    await authenticatedPage.getByTestId('delete-repository-btn').click();

    // Verify confirmation modal appears
    await expect(
      authenticatedPage.getByText('Delete Repository?'),
    ).toBeVisible();
    await expect(
      authenticatedPage.getByText(
        `You are requesting to delete the repository ${namespace}/${repoName}`,
      ),
    ).toBeVisible();
    await expect(
      authenticatedPage.getByText(
        `You must type ${namespace}/${repoName} below to confirm deletion:`,
      ),
    ).toBeVisible();

    // Type confirmation text
    await authenticatedPage
      .getByTestId('delete-repository-confirm-input')
      .fill(`${namespace}/${repoName}`);

    // Click Delete button in modal
    await authenticatedPage
      .getByTestId('delete-repository-confirm-btn')
      .click();

    // Verify redirect to repository list
    await expect(authenticatedPage).toHaveURL('/repository');

    // Verify repository no longer appears in the list
    // Wait for page to load
    await authenticatedPage.waitForLoadState('networkidle');

    // The deleted repository should not be visible
    await expect(authenticatedPage.getByText(repoName)).not.toBeVisible();

    // Verify via API that repository is actually deleted
    const verifyResponse = await authenticatedRequest.get(
      `${API_URL}/api/v1/repository/${namespace}/${repoName}`,
    );
    expect(verifyResponse.status()).toBe(404);
  });

  test('cancel button closes modal without deleting', async ({
    authenticatedPage,
    authenticatedRequest,
  }) => {
    // Navigate to repository settings
    await authenticatedPage.goto(
      `/repository/${namespace}/${repoName}?tab=settings`,
    );

    // Open delete section in sidebar
    await authenticatedPage
      .getByTestId('settings-tab-deleterepository')
      .click();

    // Click delete button
    await authenticatedPage.getByTestId('delete-repository-btn').click();

    // Verify modal is open
    await expect(
      authenticatedPage.getByText('Delete Repository?'),
    ).toBeVisible();

    // Click Cancel button
    await authenticatedPage.getByTestId('delete-repository-cancel-btn').click();

    // Verify modal is closed
    await expect(
      authenticatedPage.getByText('Delete Repository?'),
    ).not.toBeVisible();

    // Verify repository still exists via API
    const verifyResponse = await authenticatedRequest.get(
      `${API_URL}/api/v1/repository/${namespace}/${repoName}`,
      {timeout: 5000},
    );
    expect(verifyResponse.ok()).toBe(true);
  });

  test('delete button disabled without confirmation text', async ({
    authenticatedPage,
  }) => {
    // Navigate to repository settings
    await authenticatedPage.goto(
      `/repository/${namespace}/${repoName}?tab=settings`,
    );

    // Open delete section in sidebar and modal
    await authenticatedPage
      .getByTestId('settings-tab-deleterepository')
      .click();
    await authenticatedPage.getByTestId('delete-repository-btn').click();

    // Verify modal is open
    await expect(
      authenticatedPage.getByText('Delete Repository?'),
    ).toBeVisible();

    // Delete button should be disabled initially
    const deleteButton = authenticatedPage.getByTestId(
      'delete-repository-confirm-btn',
    );
    await expect(deleteButton).toBeDisabled();

    // Type partial/wrong confirmation
    await authenticatedPage
      .getByTestId('delete-repository-confirm-input')
      .fill('wrong-text');

    // Button should still be disabled
    await expect(deleteButton).toBeDisabled();

    // Type correct confirmation
    await authenticatedPage
      .getByTestId('delete-repository-confirm-input')
      .fill(`${namespace}/${repoName}`);

    // Button should now be enabled
    await expect(deleteButton).toBeEnabled();
  });
});
