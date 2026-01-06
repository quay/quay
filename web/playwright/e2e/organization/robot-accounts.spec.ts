import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {API_URL} from '../../utils/config';

test.describe(
  'Robot Accounts',
  {tag: ['@organization', '@robot-accounts']},
  () => {
    test('CRUD lifecycle: create, search, toolbar, and delete robot account', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup test organization with a robot so toolbar is visible
      const org = await api.organization('robotorg');
      await api.robot(org.name, 'existing', 'Pre-existing robot');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Robotaccounts`,
      );

      // Wait for table to load
      await expect(
        authenticatedPage.getByTestId('robot-accounts-table'),
      ).toBeVisible();

      // Verify toolbar items exist (only visible when there are robots)
      await expect(authenticatedPage.getByTestId('expand-tab')).toHaveText(
        'Expand',
      );
      await expect(authenticatedPage.getByTestId('collapse-tab')).toHaveText(
        'Collapse',
      );

      // Open and cancel modal to verify it works
      await authenticatedPage.getByTestId('create-robot-account-btn').click();
      await authenticatedPage.getByTestId('create-robot-cancel').click();

      // Create robot account via wizard
      const robotShortname = `testrobot${Date.now()}`.substring(0, 20);
      const robotDescription = 'Test robot description';

      await authenticatedPage.getByTestId('create-robot-account-btn').click();
      await authenticatedPage
        .getByTestId('robot-wizard-form-name')
        .fill(robotShortname);
      await authenticatedPage
        .getByTestId('robot-wizard-form-description')
        .fill(robotDescription);
      await authenticatedPage.getByTestId('create-robot-submit').click();

      // Verify success alert
      await expect(
        authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
      ).toContainText(
        `Successfully created robot account with robot name: ${org.name}+${robotShortname}`,
      );

      // Verify robot appears in search
      await authenticatedPage
        .getByTestId('robot-account-search')
        .fill(robotShortname);

      // Locate pagination within the Robot Accounts tab panel
      const tabPanel = authenticatedPage.getByRole('tabpanel', {
        name: 'Robot accounts',
      });
      const paginationInfo = tabPanel
        .locator('.pf-v5-c-pagination__total-items')
        .first();
      await expect(paginationInfo).toContainText('1 - 1 of 1');

      // Verify wizard states are cleared after creation
      await authenticatedPage.getByTestId('create-robot-account-btn').click();
      await expect(
        authenticatedPage.getByTestId('robot-wizard-form-name'),
      ).toHaveValue('');
      await expect(
        authenticatedPage.getByTestId('robot-wizard-form-description'),
      ).toHaveValue('');

      // Cancel and close wizard
      await authenticatedPage.getByTestId('create-robot-cancel').click();

      // Delete the robot via kebab menu
      const robotFullName = `${org.name}+${robotShortname}`;
      await authenticatedPage
        .getByTestId(`${robotFullName}-toggle-kebab`)
        .click();
      await authenticatedPage.getByTestId(`${robotFullName}-del-btn`).click();

      // Type confirmation
      await authenticatedPage
        .getByTestId('delete-confirmation-input')
        .fill('confirm');

      // Click delete button within the modal
      await authenticatedPage.getByTestId('bulk-delete-confirm-btn').click();

      // Verify success alert for deletion
      await expect(
        authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
      ).toContainText('Successfully deleted robot account');

      // Verify robot no longer appears
      await authenticatedPage.getByTestId('robot-account-search').clear();
      await authenticatedPage
        .getByTestId('robot-account-search')
        .fill(robotShortname);
      await expect(paginationInfo).toContainText('0 - 0 of 0');
    });

    test('robot credentials and Kubernetes secrets', async ({
      authenticatedPage,
      authenticatedRequest,
      api,
    }) => {
      // Setup test resources
      const org = await api.organization('k8sorg');
      const robot = await api.robot(
        org.name,
        'k8sbot',
        'Robot for K8s secret test',
      );

      // Get server hostname from config
      const configResponse = await authenticatedRequest.get(
        `${API_URL}/config`,
      );
      const config = await configResponse.json();
      const serverHostname = config.config.SERVER_HOSTNAME;

      // Get robot token from API
      const robotResponse = await authenticatedRequest.get(
        `${API_URL}/api/v1/organization/${org.name}/robots/${robot.shortname}`,
      );
      const robotData = await robotResponse.json();
      const robotToken = robotData.token;

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Robotaccounts`,
      );

      // Wait for table to be visible and click on robot
      await expect(
        authenticatedPage.getByTestId('robot-accounts-table'),
      ).toBeVisible();
      await authenticatedPage
        .locator('a')
        .filter({hasText: robot.fullName})
        .click();

      // Switch to Kubernetes secret tab
      await authenticatedPage.getByTestId('kubernetes-tab').click();

      // Verify default scope is Organization
      await expect(
        authenticatedPage.getByTestId('secret-scope-toggle'),
      ).toContainText('Organization');
      await expect(authenticatedPage.getByTestId('secret-scope')).toHaveText(
        `${serverHostname}/${org.name}`,
      );

      // Show secret content by clicking the expand button
      await authenticatedPage
        .getByTestId('step-2-secret')
        .locator('button[aria-label="Show content"]')
        .click();

      // Verify the encoded secret contains correct credentials (organization scope)
      const robotCredential = `${robot.fullName}:${robotToken}`;
      const encodedRobotCredential =
        Buffer.from(robotCredential).toString('base64');
      const expectedAuthJson = {
        auths: {
          [`${serverHostname}/${org.name}`]: {
            auth: encodedRobotCredential,
            email: '',
          },
        },
      };
      const encodedExpectedAuthJson = Buffer.from(
        JSON.stringify(expectedAuthJson, null, 2),
      ).toString('base64');

      await expect(
        authenticatedPage.getByTestId('step-2-secret').locator('pre'),
      ).toContainText(encodedExpectedAuthJson);

      // Change scope to Registry
      await authenticatedPage.getByTestId('secret-scope-toggle').click();
      await authenticatedPage
        .getByTestId('secret-scope-selector')
        .getByText('Registry')
        .click();

      // Verify scope changed
      await expect(authenticatedPage.getByTestId('secret-scope')).toHaveText(
        serverHostname,
      );

      // Verify the encoded secret with registry scope
      const expectedAuthJsonRegistry = {
        auths: {
          [serverHostname]: {
            auth: encodedRobotCredential,
            email: '',
          },
        },
      };
      const encodedExpectedAuthJsonRegistry = Buffer.from(
        JSON.stringify(expectedAuthJsonRegistry, null, 2),
      ).toString('base64');

      await expect(
        authenticatedPage.getByTestId('step-2-secret').locator('pre'),
      ).toContainText(encodedExpectedAuthJsonRegistry);
    });

    test('robot repository permissions: update single permission', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup test resources
      const org = await api.organization('permorg');
      const repo1 = await api.repository(org.name, 'permrepo1');
      const robot = await api.robot(
        org.name,
        'permbot',
        'Robot for permission test',
      );

      // Add initial permission for robot on repo1
      await api.repositoryPermission(
        org.name,
        repo1.name,
        'user',
        robot.fullName,
        'read',
      );

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Robotaccounts`,
      );

      // Wait for table to load
      await expect(
        authenticatedPage.getByTestId('robot-accounts-table'),
      ).toBeVisible();

      // Click on repository count to open permissions
      await authenticatedPage.getByText('1 repository').click();

      // Verify current selection count
      await expect(
        authenticatedPage.locator('#add-repository-bulk-select'),
      ).toContainText('1');

      // Verify initial permission is displayed correctly as 'Read'
      // This tests the fix for PROJQUAY-10084
      await expect(
        authenticatedPage.getByTestId(
          `${repo1.name}-permission-dropdown-toggle`,
        ),
      ).toContainText('Read');

      // Change permission to Admin via dropdown - use first() since there could be multiple
      await authenticatedPage.locator('#toggle-descriptions').first().click();
      await authenticatedPage.getByRole('menuitem', {name: 'Admin'}).click();

      // Save the permission change
      await authenticatedPage
        .locator('footer')
        .getByRole('button', {name: 'Save'})
        .click();

      // Verify success alert
      await expect(
        authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
      ).toContainText('Successfully updated repository permission');

      // Verify Save button is gone after successful save
      await expect(
        authenticatedPage.locator('footer').getByRole('button', {name: 'Save'}),
      ).not.toBeVisible();

      // Verify permission shows Admin - use first() since there could be multiple
      await expect(
        authenticatedPage.locator('#toggle-descriptions').first(),
      ).toContainText('Admin');
    });

    test('robot repository permissions: Write permission displays correctly (PROJQUAY-10084)', async ({
      authenticatedPage,
      api,
    }) => {
      // This test verifies the fix for PROJQUAY-10084 where the New UI was
      // incorrectly showing 'Read' permission instead of the actual permission (e.g., 'Write')
      const org = await api.organization('writepermorg');
      const repo = await api.repository(org.name, 'writerepo');
      const robot = await api.robot(
        org.name,
        'writebot',
        'Robot with Write permission',
      );

      // Add Write permission for robot on repo
      await api.repositoryPermission(
        org.name,
        repo.name,
        'user',
        robot.fullName,
        'write',
      );

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Robotaccounts`,
      );

      // Wait for table to load
      await expect(
        authenticatedPage.getByTestId('robot-accounts-table'),
      ).toBeVisible();

      // Click on repository count to open permissions modal
      await authenticatedPage.getByText('1 repository').click();

      // Verify Write permission is displayed correctly (not defaulting to 'Read')
      await expect(
        authenticatedPage.getByTestId(
          `${repo.name}-permission-dropdown-toggle`,
        ),
      ).toContainText('Write');

      // Close modal
      await authenticatedPage
        .locator('footer')
        .getByRole('button', {name: 'Close'})
        .click();

      // Reopen modal and verify permission is still Write
      await authenticatedPage.getByText('1 repository').click();
      await expect(
        authenticatedPage.getByTestId(
          `${repo.name}-permission-dropdown-toggle`,
        ),
      ).toContainText('Write');
    });

    test('robot wizard: org has 5 steps, user namespace has 3 steps', async ({
      authenticatedPage,
      api,
    }) => {
      // Part A: Verify org wizard has 5 steps
      const org = await api.organization('wizardorg');
      await api.robot(org.name, 'existing', 'Pre-existing robot');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Robotaccounts`,
      );

      // Wait for table to load
      await expect(
        authenticatedPage.getByTestId('robot-accounts-table'),
      ).toBeVisible();

      await authenticatedPage.getByTestId('create-robot-account-btn').click();

      // Wait for wizard to appear (use id selector since Modal might not pass data-testid)
      await expect(
        authenticatedPage.locator('#create-robot-account-modal'),
      ).toBeVisible();

      // Verify 5 wizard steps for organization by checking all step texts exist
      const wizardNav = authenticatedPage.locator(
        'nav[aria-label="Wizard steps"]',
      );
      await expect(
        wizardNav.getByText('Robot name and description'),
      ).toBeVisible();
      await expect(wizardNav.getByText('Add to team (optional)')).toBeVisible();
      await expect(
        wizardNav.getByText('Add to repository (optional)'),
      ).toBeVisible();
      await expect(
        wizardNav.getByText('Default permissions (optional)'),
      ).toBeVisible();
      await expect(wizardNav.getByText('Review and Finish')).toBeVisible();

      // Close org wizard
      await authenticatedPage.getByTestId('create-robot-cancel').click();

      // Part B: Verify user namespace wizard has 3 steps
      const userNamespace = TEST_USERS.user.username;
      await authenticatedPage.goto(
        `/organization/${userNamespace}?tab=Robotaccounts`,
      );

      // For user namespace, might show empty state with different button
      await authenticatedPage
        .getByRole('button', {name: 'Create robot account'})
        .click();

      // Wait for wizard to appear (use id selector since Modal might not pass data-testid)
      await expect(
        authenticatedPage.locator('#create-robot-account-modal'),
      ).toBeVisible();

      // Verify only 3 steps for user namespace (no teams, no default permissions)
      const userWizardNav = authenticatedPage.locator(
        'nav[aria-label="Wizard steps"]',
      );
      await expect(
        userWizardNav.getByText('Robot name and description'),
      ).toBeVisible();
      await expect(
        userWizardNav.getByText('Add to repository (optional)'),
      ).toBeVisible();
      await expect(userWizardNav.getByText('Review and Finish')).toBeVisible();

      // Verify teams and default permissions steps don't exist for user namespace
      await expect(
        userWizardNav.getByText('Add to team (optional)'),
      ).not.toBeVisible();
      await expect(
        userWizardNav.getByText('Default permissions (optional)'),
      ).not.toBeVisible();

      // Part C: Create robot in user namespace
      const userRobotShortname = `userbot${Date.now()}`.substring(0, 20);
      const userRobotDescription = 'User namespace robot';

      await authenticatedPage
        .getByTestId('robot-wizard-form-name')
        .fill(userRobotShortname);
      await authenticatedPage
        .getByTestId('robot-wizard-form-description')
        .fill(userRobotDescription);
      await authenticatedPage.getByTestId('create-robot-submit').click();

      // Verify success alert
      await expect(
        authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
      ).toContainText(
        `Successfully created robot account with robot name: ${userNamespace}+${userRobotShortname}`,
      );

      // Verify robot appears in search
      await authenticatedPage
        .getByTestId('robot-account-search')
        .fill(userRobotShortname);
      const tabPanel = authenticatedPage.getByRole('tabpanel', {
        name: 'Robot accounts',
      });
      const paginationInfo = tabPanel
        .locator('.pf-v5-c-pagination__total-items')
        .first();
      await expect(paginationInfo).toContainText('1 - 1 of 1');
    });

    test.describe(
      'with ROBOTS_DISALLOW enabled',
      {tag: '@config:ROBOTS_DISALLOW'},
      () => {
        // Skip ALL tests in this block if ROBOTS_DISALLOW is not enabled
        test.beforeEach(async ({quayConfig}) => {
          test.skip(
            quayConfig?.config?.ROBOTS_DISALLOW !== true,
            'ROBOTS_DISALLOW is not enabled',
          );
        });

        test('empty state shows disabled message and hides create button', async ({
          authenticatedPage,
          api,
        }) => {
          // Create org with no robots
          const org = await api.organization('robotdisallow');

          await authenticatedPage.goto(
            `/organization/${org.name}?tab=Robotaccounts`,
          );

          // Verify empty state message indicates robots are disabled
          await expect(
            authenticatedPage.getByText('Robot accounts have been disabled'),
          ).toBeVisible();

          // Verify create button is NOT visible in empty state
          await expect(
            authenticatedPage.getByRole('button', {
              name: 'Create robot account',
            }),
          ).not.toBeVisible();
        });
      },
    );
  },
);
