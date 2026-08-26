import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {API_URL} from '../../utils/config';
import {pushImage, pullImage} from '../../utils/container';

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
        authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
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
        .locator('.pf-v6-c-pagination__total-items')
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
        authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
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

    test('Docker Configuration tab shows auth.json content and download link', async ({
      authenticatedPage,
      authenticatedRequest,
      api,
    }) => {
      const org = await api.organization('dockercfgorg');
      const robot = await api.robot(
        org.name,
        'dockerbot',
        'Robot for Docker config test',
      );

      // Get robot token from API
      const robotResponse = await authenticatedRequest.get(
        `${API_URL}/api/v1/organization/${org.name}/robots/${robot.shortname}`,
      );
      const robotData = await robotResponse.json();
      const robotToken = robotData.token;

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Robotaccounts`,
      );

      // Wait for table and click on robot
      await expect(
        authenticatedPage.getByTestId('robot-accounts-table'),
      ).toBeVisible({timeout: 15000});
      await authenticatedPage
        .locator('a')
        .filter({hasText: robot.fullName})
        .click();

      // Switch to Docker Configuration tab
      await authenticatedPage.getByTestId('docker-config-tab').click();

      // Expand the config content
      await authenticatedPage
        .getByTestId('docker-config-content')
        .locator('button[aria-label="Show content"]')
        .click();

      // Verify the Docker config contains correct auth encoding (organization scope)
      const robotCredential = `${robot.fullName}:${robotToken}`;
      const encodedRobotCredential =
        Buffer.from(robotCredential).toString('base64');

      await expect(
        authenticatedPage.getByTestId('docker-config-content').locator('pre'),
      ).toContainText(encodedRobotCredential);

      // Verify download link is present with correct filename
      const escapedName = robot.fullName.replace(/[^a-zA-Z0-9]/g, '-');
      const expectedFilename = `${escapedName}-auth.json`;
      await expect(
        authenticatedPage.getByTestId('docker-config-download'),
      ).toContainText(expectedFilename);

      // Verify mv command is shown (ClipboardCopy stores value in an input)
      await expect(
        authenticatedPage.locator('#docker-config-mv input'),
      ).toHaveValue(`mv ${escapedName}-auth.json ~/.docker/config.json`);
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
        authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
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
        authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
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
        .locator('.pf-v6-c-pagination__total-items')
        .first();
      await expect(paginationInfo).toContainText('1 - 1 of 1');
    });

    test('robot wizard: Default permissions dropdown shows None by default', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('defpermorg');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Robotaccounts`,
      );

      // Open the create robot account wizard
      await authenticatedPage
        .getByRole('button', {name: 'Create robot account'})
        .click();
      await expect(
        authenticatedPage.locator('#create-robot-account-modal'),
      ).toBeVisible();

      // Fill in robot name to enable navigation
      await authenticatedPage
        .getByTestId('robot-wizard-form-name')
        .fill('defpermbot');

      // Navigate to Default permissions step via wizard nav
      const wizardNav = authenticatedPage.locator(
        'nav[aria-label="Wizard steps"]',
      );
      await wizardNav.getByText('Default permissions (optional)').click();

      // Verify the permission dropdown toggle shows 'None'
      await expect(
        authenticatedPage.locator('#toggle-descriptions'),
      ).toContainText('None');

      // Verify changing the dropdown works
      await authenticatedPage.locator('#toggle-descriptions').click();
      await authenticatedPage.getByTestId('Read-permission-type').click();
      await expect(
        authenticatedPage.locator('#toggle-descriptions'),
      ).toContainText('Read');

      // Change back to None and verify
      await authenticatedPage.locator('#toggle-descriptions').click();
      await authenticatedPage.getByTestId('None-permission-type').click();
      await expect(
        authenticatedPage.locator('#toggle-descriptions'),
      ).toContainText('None');
    });

    test('robot wizard: selecting None permission deselects the repository (PROJQUAY-10931)', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nonepermorg');
      const repo = await api.repository(org.name, 'nonerepo');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Robotaccounts`,
      );

      // Open the create robot account wizard
      await authenticatedPage
        .getByRole('button', {name: 'Create robot account'})
        .click();
      await expect(
        authenticatedPage.locator('#create-robot-account-modal'),
      ).toBeVisible();

      // Fill in robot name to enable navigation
      await authenticatedPage
        .getByTestId('robot-wizard-form-name')
        .fill('nonebot');

      // Navigate to "Add to repository" step
      const wizardNav = authenticatedPage.locator(
        'nav[aria-label="Wizard steps"]',
      );
      await wizardNav.getByText('Add to repository (optional)').click();

      // Select the repository checkbox
      await authenticatedPage
        .getByTestId(`checkbox-row-${repo.name}`)
        .locator('input[type="checkbox"]')
        .click();

      // Verify it defaults to "Read" when selected
      await expect(
        authenticatedPage.getByTestId(
          `${repo.name}-permission-dropdown-toggle`,
        ),
      ).toContainText('Read');

      // Change permission to "None"
      await authenticatedPage
        .getByTestId(`${repo.name}-permission-dropdown-toggle`)
        .click();
      await authenticatedPage.getByTestId('None-permission-type').click();

      // Verify the dropdown shows "None" (not reverting to "Read")
      await expect(
        authenticatedPage.getByTestId(
          `${repo.name}-permission-dropdown-toggle`,
        ),
      ).toContainText('None');

      // Verify the row checkbox is now unchecked
      await expect(
        authenticatedPage
          .getByTestId(`checkbox-row-${repo.name}`)
          .locator('input[type="checkbox"]'),
      ).not.toBeChecked();

      // Re-select the row and verify it defaults back to "Read"
      await authenticatedPage
        .getByTestId(`checkbox-row-${repo.name}`)
        .locator('input[type="checkbox"]')
        .click();
      await expect(
        authenticatedPage.getByTestId(
          `${repo.name}-permission-dropdown-toggle`,
        ),
      ).toContainText('Read');
    });

    test('bulk delete multiple robot accounts', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('bulkdelrobotorg');
      await api.robot(org.name, 'bulkrobot1', 'First robot');
      await api.robot(org.name, 'bulkrobot2', 'Second robot');
      await api.robot(org.name, 'bulkrobot3', 'Third robot');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Robotaccounts`,
      );
      await expect(
        authenticatedPage.getByTestId('robot-accounts-table'),
      ).toBeVisible();

      // Select all robots via toolbar checkbox
      await authenticatedPage
        .getByRole('checkbox', {name: 'Select all'})
        .check({force: true});

      // Click the bulk delete action in the toolbar
      await authenticatedPage
        .getByRole('button', {name: 'Delete selected items'})
        .click();

      // Confirm bulk deletion
      await authenticatedPage
        .getByTestId('delete-confirmation-input')
        .fill('confirm');
      await authenticatedPage.getByTestId('bulk-delete-confirm-btn').click();

      // Verify success alert
      await expect(
        authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
      ).toContainText('Successfully deleted robot account');

      // Verify empty state
      await expect(
        authenticatedPage.getByText('There are no viewable robot accounts'),
      ).toBeVisible({timeout: 15000});
    });

    test('robot wizard search state is isolated from org page search (PROJQUAY-11236)', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('searchiso');
      const repo1 = await api.repository(org.name, 'alpha');
      const repo2 = await api.repository(org.name, 'beta');
      const team = await api.team(org.name, 'searchteam');

      // Step 1: Search repositories on the org Repositories tab
      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Repositories`,
      );
      const repoSearch = authenticatedPage.getByPlaceholder('Search by name');
      await expect(repoSearch).toBeVisible();
      await repoSearch.fill(repo1.name);

      // Verify the search filtered results
      await expect(
        authenticatedPage.getByRole('link', {name: repo1.name}),
      ).toBeVisible();

      // Step 2: Switch to Robot Accounts tab via tab click (not goto, to
      // preserve in-memory search state on the Repositories tab)
      await authenticatedPage
        .getByRole('tab', {name: 'Robot accounts'})
        .click();
      await authenticatedPage
        .getByRole('button', {name: 'Create robot account'})
        .click();
      await expect(
        authenticatedPage.locator('#create-robot-account-modal'),
      ).toBeVisible();

      // Fill robot name so wizard navigation is enabled
      await authenticatedPage
        .getByTestId('robot-wizard-form-name')
        .fill('isobot');

      // Navigate to "Add to repository" step
      const wizardNav = authenticatedPage.locator(
        'nav[aria-label="Wizard steps"]',
      );
      await wizardNav.getByText('Add to repository (optional)').click();

      // Verify wizard repo search is empty (not polluted by org page search)
      const wizardRepoSearch = authenticatedPage.getByTestId(
        'robot-wizard-repo-search',
      );
      await expect(wizardRepoSearch).toBeVisible();
      await expect(wizardRepoSearch).toHaveValue('');

      // Both repos should be visible (no filter applied).
      // PatternFly tables may use role="gridcell", so match by text within
      // the wizard modal instead of relying on the cell role.
      const modal = authenticatedPage.locator('#create-robot-account-modal');
      await expect(modal.getByText(repo1.name)).toBeVisible();
      await expect(modal.getByText(repo2.name)).toBeVisible();

      // Type in the wizard's repo search and verify it filters
      await wizardRepoSearch.fill(repo2.name);
      await expect(modal.getByText(repo2.name)).toBeVisible();
      await expect(modal.getByText(repo1.name)).not.toBeVisible();

      // Navigate to "Add to team" step
      await wizardNav.getByText('Add to team (optional)').click();

      // Verify wizard team search is empty (FilterWithDropdown uses a
      // different component, so match by placeholder instead of testId)
      const wizardTeamSearch = modal.getByPlaceholder('Search, create team');
      await expect(wizardTeamSearch).toBeVisible();
      await expect(wizardTeamSearch).toHaveValue('');

      // Team should be visible (no filter applied)
      await expect(modal.getByText(team.name)).toBeVisible();

      // Close the wizard
      await authenticatedPage.getByTestId('create-robot-cancel').click();

      // Step 3: Go back to Repositories tab via tab click (preserves state)
      await authenticatedPage.getByRole('tab', {name: 'Repositories'}).click();
      const repoSearchAfter =
        authenticatedPage.getByPlaceholder('Search by name');
      await expect(repoSearchAfter).toBeVisible();

      // The repo list search should still show the original search text
      // (not polluted by the wizard's search)
      await expect(repoSearchAfter).toHaveValue(repo1.name);
    });

    test.describe('pagination with large datasets', () => {
      const ITEM_COUNT = 21;

      test('pagination in "Add to team" wizard step with >20 teams', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization('paginateteam');

        // Orgs start with an auto-created "owners" team
        for (let i = 0; i < ITEM_COUNT - 1; i++) {
          await api.team(org.name, `team${String(i).padStart(2, '0')}`);
        }

        await authenticatedPage.goto(
          `/organization/${org.name}?tab=Robotaccounts`,
        );

        await authenticatedPage
          .getByRole('button', {name: 'Create robot account'})
          .click();
        await expect(
          authenticatedPage.locator('#create-robot-account-modal'),
        ).toBeVisible();

        await authenticatedPage
          .getByTestId('robot-wizard-form-name')
          .fill('paginatebot');

        const wizardNav = authenticatedPage.locator(
          'nav[aria-label="Wizard steps"]',
        );
        await wizardNav.getByText('Add to team (optional)').click();

        const modal = authenticatedPage.locator('#create-robot-account-modal');
        const paginationInfo = modal
          .locator('.pf-v6-c-pagination__total-items')
          .first();
        await expect(paginationInfo).toContainText(`1 - 20 of ${ITEM_COUNT}`);

        await modal
          .getByRole('button', {name: 'Go to next page'})
          .first()
          .click();
        await expect(paginationInfo).toContainText(
          `21 - ${ITEM_COUNT} of ${ITEM_COUNT}`,
        );

        await modal
          .getByRole('button', {name: 'Go to previous page'})
          .first()
          .click();
        await expect(paginationInfo).toContainText(`1 - 20 of ${ITEM_COUNT}`);
      });

      test('pagination in "Add to repository" wizard step with >20 repos', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization('paginaterepo');

        for (let i = 0; i < ITEM_COUNT; i++) {
          await api.repository(org.name, `repo${String(i).padStart(2, '0')}`);
        }

        await authenticatedPage.goto(
          `/organization/${org.name}?tab=Robotaccounts`,
        );

        await authenticatedPage
          .getByRole('button', {name: 'Create robot account'})
          .click();
        await expect(
          authenticatedPage.locator('#create-robot-account-modal'),
        ).toBeVisible();

        await authenticatedPage
          .getByTestId('robot-wizard-form-name')
          .fill('paginatebot');

        const wizardNav = authenticatedPage.locator(
          'nav[aria-label="Wizard steps"]',
        );
        await wizardNav.getByText('Add to repository (optional)').click();

        const modal = authenticatedPage.locator('#create-robot-account-modal');
        const paginationInfo = modal
          .locator('.pf-v6-c-pagination__total-items')
          .first();
        await expect(paginationInfo).toContainText(`1 - 20 of ${ITEM_COUNT}`);

        await modal
          .getByRole('button', {name: 'Go to next page'})
          .first()
          .click();
        await expect(paginationInfo).toContainText(
          `21 - ${ITEM_COUNT} of ${ITEM_COUNT}`,
        );

        await modal
          .getByRole('button', {name: 'Go to previous page'})
          .first()
          .click();
        await expect(paginationInfo).toContainText(`1 - 20 of ${ITEM_COUNT}`);
      });

      test('pagination in robot account table with >20 robots', async ({
        authenticatedPage,
        api,
      }) => {
        const org = await api.organization('paginaterobots');

        for (let i = 0; i < ITEM_COUNT; i++) {
          await api.robot(org.name, `bot${String(i).padStart(2, '0')}`);
        }

        await authenticatedPage.goto(
          `/organization/${org.name}?tab=Robotaccounts`,
        );

        await expect(
          authenticatedPage.getByTestId('robot-accounts-table'),
        ).toBeVisible();

        const tabPanel = authenticatedPage.getByRole('tabpanel', {
          name: 'Robot accounts',
        });
        const paginationInfo = tabPanel
          .locator('.pf-v6-c-pagination__total-items')
          .first();
        await expect(paginationInfo).toContainText(`1 - 20 of ${ITEM_COUNT}`);

        await tabPanel
          .getByRole('button', {name: 'Go to next page'})
          .first()
          .click();
        await expect(paginationInfo).toContainText(
          `21 - ${ITEM_COUNT} of ${ITEM_COUNT}`,
        );

        await tabPanel
          .getByRole('button', {name: 'Go to previous page'})
          .first()
          .click();
        await expect(paginationInfo).toContainText(`1 - 20 of ${ITEM_COUNT}`);
      });
    });

    test.describe('robot credential execution', {tag: ['@container']}, () => {
      test('robot credentials can authenticate via container login', async ({
        api,
      }) => {
        const org = await api.organization('robotloginorg');
        const repo = await api.repository(org.name, 'logintestrepo');
        const robot = await api.robot(
          org.name,
          'loginbot',
          'Robot for login test',
        );

        await api.repositoryPermission(
          org.name,
          repo.name,
          'user',
          robot.fullName,
          'write',
        );

        await pushImage(
          org.name,
          repo.name,
          'latest',
          robot.fullName,
          robot.token,
        );
      });

      test('robot credentials can push and pull images', async ({api}) => {
        const org = await api.organization('robotpushpullorg');
        const repo = await api.repository(org.name, 'pushpullrepo');
        const robot = await api.robot(
          org.name,
          'pushpullbot',
          'Robot for push/pull test',
        );

        await api.repositoryPermission(
          org.name,
          repo.name,
          'user',
          robot.fullName,
          'write',
        );

        await pushImage(
          org.name,
          repo.name,
          'v1.0',
          robot.fullName,
          robot.token,
        );

        await pullImage(
          org.name,
          repo.name,
          'v1.0',
          robot.fullName,
          robot.token,
        );
      });

      test('robot token format is valid and non-empty', async ({
        authenticatedRequest,
        api,
      }) => {
        const org = await api.organization('robottokenorg');
        const robot = await api.robot(
          org.name,
          'tokenbot',
          'Robot for token validation',
        );

        expect(robot.fullName).toMatch(/^.+\+.+$/);
        expect(robot.token).toBeTruthy();
        expect(robot.token.length).toBeGreaterThan(0);

        const robotResponse = await authenticatedRequest.get(
          `${API_URL}/api/v1/organization/${org.name}/robots/${robot.shortname}`,
        );
        const robotData = await robotResponse.json();
        expect(robotData.token).toBe(robot.token);
      });
    });

    test(
      'robot wizard fits within modal without overflow (PROJQUAY-12151)',
      {tag: '@PROJQUAY-12151'},
      async ({authenticatedPage, api}) => {
        const org = await api.organization('wizoverflow');

        await authenticatedPage.goto(
          `/organization/${org.name}?tab=Robotaccounts`,
        );

        await authenticatedPage
          .getByRole('button', {name: 'Create robot account'})
          .click();

        const modal = authenticatedPage.locator('#create-robot-account-modal');
        await expect(modal).toBeVisible();

        const wizard = modal.locator('.pf-v6-c-wizard');
        await expect(wizard).toBeVisible();

        const modalBox = await modal.boundingBox();
        const wizardBox = await wizard.boundingBox();

        expect(modalBox).not.toBeNull();
        expect(wizardBox).not.toBeNull();
        if (modalBox && wizardBox) {
          expect(wizardBox.width).toBeLessThanOrEqual(modalBox.width);
          expect(wizardBox.x).toBeGreaterThanOrEqual(modalBox.x);
          expect(wizardBox.x + wizardBox.width).toBeLessThanOrEqual(
            modalBox.x + modalBox.width + 1,
          );
        }
      },
    );

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
