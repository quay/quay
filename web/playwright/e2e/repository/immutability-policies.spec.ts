import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {pushImage} from '../../utils/container';

test.describe(
  'Immutability Policies',
  {tag: ['@repository', '@feature:IMMUTABLE_TAGS']},
  () => {
    test.describe('Organization Settings', () => {
      test('can create an immutability policy', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization();

        await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

        // Navigate to Immutability Policies tab
        await authenticatedPage.getByTestId('Immutability Policies').click();

        // Click "Add Policy" button in empty state
        await authenticatedPage
          .getByTestId('add-immutability-policy-btn')
          .click();

        // Fill in the policy form
        await authenticatedPage
          .getByTestId('immutability-tag-pattern')
          .fill('v[0-9]+\\..*');

        // Save the policy
        await authenticatedPage
          .getByTestId('save-immutability-policy-btn')
          .click();

        // Verify success message
        await expect(
          authenticatedPage.getByText(
            'Successfully created immutability policy',
          ),
        ).toBeVisible();
      });

      test('can update an existing immutability policy', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization();
        await api.orgImmutabilityPolicy(org.name, 'v[0-9]+\\..*', true);

        await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

        // Navigate to Immutability Policies tab
        await authenticatedPage.getByTestId('Immutability Policies').click();

        // Wait for policy to load in table
        await expect(
          authenticatedPage.getByTestId('immutability-tag-pattern-display'),
        ).toContainText('v[0-9]+\\..*');

        // Click edit button to enter edit mode
        await authenticatedPage
          .getByTestId('edit-immutability-policy-btn')
          .click();

        // Update the pattern
        await authenticatedPage
          .getByTestId('immutability-tag-pattern')
          .fill('release-.*');

        // Save the policy
        await authenticatedPage
          .getByTestId('save-immutability-policy-btn')
          .click();

        // Verify success message
        await expect(
          authenticatedPage.getByText(
            'Successfully updated immutability policy',
          ),
        ).toBeVisible();
      });

      test('can delete an immutability policy', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization();
        await api.orgImmutabilityPolicy(org.name, 'v[0-9]+\\..*', true);

        await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

        // Navigate to Immutability Policies tab
        await authenticatedPage.getByTestId('Immutability Policies').click();

        // Wait for policy to load in table
        await expect(
          authenticatedPage.getByTestId('immutability-tag-pattern-display'),
        ).toContainText('v[0-9]+\\..*');

        // Delete the policy (button is in table row)
        await authenticatedPage
          .getByTestId('delete-immutability-policy-btn')
          .click();

        // Verify success message
        await expect(
          authenticatedPage.getByText(
            'Successfully deleted immutability policy',
          ),
        ).toBeVisible();
      });

      test('validates regex pattern', async ({authenticatedPage, api}) => {
        const org = await api.organization();

        await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

        // Navigate to Immutability Policies tab
        await authenticatedPage.getByTestId('Immutability Policies').click();

        // Click "Add Policy" button in empty state
        await authenticatedPage
          .getByTestId('add-immutability-policy-btn')
          .click();

        // Enter invalid regex pattern
        await authenticatedPage
          .getByTestId('immutability-tag-pattern')
          .fill('[invalid');

        // Try to save
        await authenticatedPage
          .getByTestId('save-immutability-policy-btn')
          .click();

        // Verify validation error
        await expect(
          authenticatedPage.getByText('Invalid regular expression pattern'),
        ).toBeVisible();
      });

      test('can create policy with excludes behavior', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization();

        await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

        // Navigate to Immutability Policies tab
        await authenticatedPage.getByTestId('Immutability Policies').click();

        // Click "Add Policy" button in empty state
        await authenticatedPage
          .getByTestId('add-immutability-policy-btn')
          .click();

        // Fill in the pattern
        await authenticatedPage
          .getByTestId('immutability-tag-pattern')
          .fill('dev-.*');

        // Select "does not match" behavior
        await authenticatedPage
          .getByTestId('immutability-pattern-behavior')
          .selectOption('doesnotmatch');

        // Verify helper text updates
        await expect(
          authenticatedPage.getByText(
            'Tags that do NOT match the pattern will be immutable',
          ),
        ).toBeVisible();

        // Save the policy
        await authenticatedPage
          .getByTestId('save-immutability-policy-btn')
          .click();

        // Verify success message
        await expect(
          authenticatedPage.getByText(
            'Successfully created immutability policy',
          ),
        ).toBeVisible();
      });

      test('logs immutability policy actions in usage logs', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization();
        const tagPattern = 'v[0-9]+\\..*';

        // Create a policy via API to generate a log entry
        await api.orgImmutabilityPolicy(org.name, tagPattern, true);

        // Navigate to Usage Logs tab
        await authenticatedPage.goto(`/organization/${org.name}?tab=Logs`);

        // Wait for table to load
        await expect(
          authenticatedPage.getByTestId('usage-logs-table'),
        ).toBeVisible();

        // Filter by "immutability" to find our log entry
        await authenticatedPage
          .getByPlaceholder('Filter logs')
          .fill('immutability');

        // Give filter time to apply
        await authenticatedPage.waitForTimeout(500);

        // Verify the create immutability policy log entry is visible
        await expect(
          authenticatedPage
            .getByTestId('usage-logs-table')
            .getByText('Created immutability policy'),
        ).toBeVisible();

        // Verify the pattern is shown in the log
        await expect(
          authenticatedPage
            .getByTestId('usage-logs-table')
            .getByText(tagPattern),
        ).toBeVisible();
      });

      test('can add multiple policies', async ({authenticatedPage, api}) => {
        const org = await api.organization();
        await api.orgImmutabilityPolicy(org.name, 'v[0-9]+\\..*', true);

        await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

        // Navigate to Immutability Policies tab
        await authenticatedPage.getByTestId('Immutability Policies').click();

        // Verify existing policy shows in table
        await expect(
          authenticatedPage.getByTestId('immutability-tag-pattern-display'),
        ).toContainText('v[0-9]+\\..*');

        // Click Add Policy button
        await authenticatedPage
          .getByTestId('add-immutability-policy-btn')
          .click();

        // There should now be an inline form for new policy and existing policy in table
        await expect(
          authenticatedPage.getByTestId('immutability-tag-pattern'),
        ).toBeVisible();
        await expect(
          authenticatedPage.getByTestId('immutability-tag-pattern-display'),
        ).toBeVisible();
      });
    });

    test.describe('Repository Settings', () => {
      test('can create a repository immutability policy', async ({
        authenticatedPage,
        api,
      }) => {
        const repo = await api.repository();

        await authenticatedPage.goto(
          `/repository/${repo.fullName}?tab=settings`,
        );

        // Navigate to Repository Immutability Policies tab
        await authenticatedPage
          .getByTestId('settings-tab-repositoryimmutabilitypolicies')
          .click();

        // Click "Add Policy" button in empty state
        await authenticatedPage
          .getByTestId('add-repo-immutability-policy-btn')
          .click();

        // Fill in the policy form
        await authenticatedPage
          .getByTestId('immutability-tag-pattern')
          .fill('release-.*');

        // Save the policy
        await authenticatedPage
          .getByTestId('save-immutability-policy-btn')
          .click();

        // Verify success message
        await expect(
          authenticatedPage.getByText(
            'Successfully created repository immutability policy',
          ),
        ).toBeVisible();
      });

      test('shows inherited namespace policies', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization();
        await api.orgImmutabilityPolicy(org.name, 'v[0-9]+\\..*', true);
        const repo = await api.repository(org.name);

        await authenticatedPage.goto(
          `/repository/${repo.fullName}?tab=settings`,
        );

        // Navigate to Repository Immutability Policies tab
        await authenticatedPage
          .getByTestId('settings-tab-repositoryimmutabilitypolicies')
          .click();

        // Verify inherited namespace policy shows in table with Namespace scope
        await expect(
          authenticatedPage.getByText('Namespace', {exact: true}),
        ).toBeVisible();

        // Verify the pattern is displayed
        await expect(
          authenticatedPage.getByTestId('immutability-tag-pattern-display'),
        ).toContainText('v[0-9]+\\..*');

        // Verify it shows as "Inherited" (no edit/delete buttons)
        await expect(authenticatedPage.getByText('Inherited')).toBeVisible();
      });

      test('can delete a repository immutability policy', async ({
        authenticatedPage,
        api,
      }) => {
        const repo = await api.repository();
        await api.repoImmutabilityPolicy(
          repo.namespace,
          repo.name,
          'release-.*',
          true,
        );

        await authenticatedPage.goto(
          `/repository/${repo.fullName}?tab=settings`,
        );

        // Navigate to Repository Immutability Policies tab
        await authenticatedPage
          .getByTestId('settings-tab-repositoryimmutabilitypolicies')
          .click();

        // Wait for policy to load in table
        await expect(
          authenticatedPage.getByTestId('immutability-tag-pattern-display'),
        ).toContainText('release-.*');

        // Delete the policy (button is in table row)
        await authenticatedPage
          .getByTestId('delete-immutability-policy-btn')
          .click();

        // Verify success message
        await expect(
          authenticatedPage.getByText(
            'Successfully deleted repository immutability policy',
          ),
        ).toBeVisible();
      });
    });

    test.describe('Policy Effects', {tag: ['@container']}, () => {
      test('policy makes matching tags immutable on push', async ({
        authenticatedPage,
        api,
      }) => {
        const repo = await api.repository();
        await api.repoImmutabilityPolicy(
          repo.namespace,
          repo.name,
          'v[0-9]+\\..*',
          true,
        );

        // Push an image with a matching tag
        await pushImage(
          repo.namespace,
          repo.name,
          'v1.0.0',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );

        await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

        // Verify tag is visible and has lock icon
        await expect(
          authenticatedPage.getByRole('link', {name: 'v1.0.0'}),
        ).toBeVisible();

        const tagRow = authenticatedPage
          .getByRole('row')
          .filter({has: authenticatedPage.getByRole('link', {name: 'v1.0.0'})});

        await expect(tagRow.getByTestId('immutable-tag-icon')).toBeVisible({
          timeout: 10000,
        });

        // Verify delete action is disabled
        await tagRow.getByLabel('Tag actions kebab').click();
        const removeAction = authenticatedPage.getByRole('menuitem', {
          name: 'Remove',
          exact: true,
        });
        await expect(removeAction).toBeDisabled();
      });

      test('non-matching tags are not affected by policy', async ({
        authenticatedPage,
        api,
      }) => {
        const repo = await api.repository();
        await api.repoImmutabilityPolicy(
          repo.namespace,
          repo.name,
          'release-.*',
          true,
        );

        // Push an image with a non-matching tag
        await pushImage(
          repo.namespace,
          repo.name,
          'dev-build',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );

        await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

        // Verify tag is visible and does NOT have lock icon
        await expect(
          authenticatedPage.getByRole('link', {name: 'dev-build'}),
        ).toBeVisible();

        const tagRow = authenticatedPage.getByRole('row').filter({
          has: authenticatedPage.getByRole('link', {name: 'dev-build'}),
        });

        await expect(
          tagRow.getByTestId('immutable-tag-icon'),
        ).not.toBeVisible();

        // Verify delete action is enabled
        await tagRow.getByLabel('Tag actions kebab').click();
        const removeAction = authenticatedPage.getByRole('menuitem', {
          name: 'Remove',
          exact: true,
        });
        await expect(removeAction).toBeEnabled();
      });

      test('excludes pattern makes non-matching tags immutable', async ({
        authenticatedPage,
        api,
      }) => {
        const repo = await api.repository();
        // Pattern: dev-.*, tagPatternMatches: false
        // This means tags NOT matching dev-.* will be immutable
        await api.repoImmutabilityPolicy(
          repo.namespace,
          repo.name,
          'dev-.*',
          false,
        );

        // Push matching tag (dev-build) - should NOT be immutable
        await pushImage(
          repo.namespace,
          repo.name,
          'dev-build',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );

        // Push non-matching tag (v1.0.0) - should be immutable
        await pushImage(
          repo.namespace,
          repo.name,
          'v1.0.0',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );

        await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

        // dev-build should NOT be immutable
        const devRow = authenticatedPage.getByRole('row').filter({
          has: authenticatedPage.getByRole('link', {name: 'dev-build'}),
        });
        await expect(
          devRow.getByTestId('immutable-tag-icon'),
        ).not.toBeVisible();

        // v1.0.0 should be immutable
        const releaseRow = authenticatedPage
          .getByRole('row')
          .filter({has: authenticatedPage.getByRole('link', {name: 'v1.0.0'})});
        await expect(releaseRow.getByTestId('immutable-tag-icon')).toBeVisible({
          timeout: 10000,
        });
      });

      test('namespace policy applies to repository tags', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization();
        await api.orgImmutabilityPolicy(org.name, 'v[0-9]+\\..*', true);
        const repo = await api.repository(org.name);

        // Push an image with a matching tag
        await pushImage(
          repo.namespace,
          repo.name,
          'v1.0.0',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );

        await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

        // Verify tag is immutable due to namespace policy
        await expect(
          authenticatedPage.getByRole('link', {name: 'v1.0.0'}),
        ).toBeVisible();

        const tagRow = authenticatedPage
          .getByRole('row')
          .filter({has: authenticatedPage.getByRole('link', {name: 'v1.0.0'})});

        await expect(tagRow.getByTestId('immutable-tag-icon')).toBeVisible({
          timeout: 10000,
        });
      });
    });

    test.describe('Error Handling', () => {
      test('displays error for duplicate policy pattern', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization();
        await api.orgImmutabilityPolicy(org.name, 'v[0-9]+\\..*', true);

        await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

        // Navigate to Immutability Policies tab
        await authenticatedPage.getByTestId('Immutability Policies').click();

        // Add a new policy
        await authenticatedPage
          .getByTestId('add-immutability-policy-btn')
          .click();

        // Find the second policy form (Policy 2) and fill the same pattern
        const secondPatternInput = authenticatedPage
          .locator('#immutability-policy-form-1')
          .getByTestId('immutability-tag-pattern');

        await secondPatternInput.fill('v[0-9]+\\..*');

        // Try to save (find the save button in the second form)
        const secondSaveButton = authenticatedPage
          .locator('#immutability-policy-form-1')
          .getByTestId('save-immutability-policy-btn');

        await secondSaveButton.click();

        // Verify error message for duplicate
        await expect(
          authenticatedPage.getByText('Could not create immutability policy'),
        ).toBeVisible();
      });

      test('rejects same pattern with different matches behavior', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization();
        // Create a policy with tagPatternMatches=true
        await api.orgImmutabilityPolicy(org.name, 'dev-.*', true);

        await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

        // Navigate to Immutability Policies tab
        await authenticatedPage.getByTestId('Immutability Policies').click();

        // Add a new policy with the same pattern but opposite behavior
        await authenticatedPage
          .getByTestId('add-immutability-policy-btn')
          .click();

        const secondForm = authenticatedPage.locator(
          '#immutability-policy-form-1',
        );

        await secondForm.getByTestId('immutability-tag-pattern').fill('dev-.*');

        // Select "does not match" behavior (opposite of the existing policy)
        await secondForm
          .getByTestId('immutability-pattern-behavior')
          .selectOption('doesnotmatch');

        await secondForm.getByTestId('save-immutability-policy-btn').click();

        // Verify error - same pattern should be rejected regardless of matches behavior
        await expect(
          authenticatedPage.getByText('Could not create immutability policy'),
        ).toBeVisible();
      });
    });
  },
);
