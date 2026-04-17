import {test, expect} from '../../fixtures';

/**
 * Bug Discovery Tests: Robot Account Permission Management
 *
 * These tests reproduce potential UI bugs found via static analysis
 * of the robot account wizard and kebab menu components.
 */
test.describe(
  'Bug Discovery: Robot Account Permissions',
  {tag: ['@bug-discovery', '@organization']},
  () => {
    test('robot account kebab menu should not throw on select', async ({
      authenticatedPage,
      api,
    }) => {
      // Bug: RobotAccountKebab.tsx:17-20
      // The onSelect handler calls document.getElementById() to find the
      // kebab toggle element and calls .focus() on it WITHOUT a null check.
      // If the element is not found (e.g., DOM not ready, element removed),
      // this throws a TypeError: Cannot read properties of null
      //
      // Expected behavior: kebab menu closes and returns focus cleanly
      // Actual behavior: potential null dereference crash

      const org = await api.organization('robotkebab');
      const robot = await api.robot(org.name, 'testbot');

      // Navigate to the organization's robot accounts page
      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Robotaccounts`,
      );

      // Wait for robot account to appear — use fullName for unambiguous match
      const robotRow = authenticatedPage.locator('tr', {
        hasText: robot.fullName,
      });
      await expect(robotRow).toBeVisible();

      // Open the kebab menu for this robot account
      const kebab = authenticatedPage.getByTestId(
        `${org.name}+${robot.shortname}-toggle-kebab`,
      );
      await kebab.click();

      // Verify dropdown items are visible
      await expect(
        authenticatedPage.getByTestId(
          `${org.name}+${robot.shortname}-set-repo-perms-btn`,
        ),
      ).toBeVisible();

      // Click "Set repository permissions" — this triggers onSelect which calls
      // document.getElementById().focus() without null check
      await authenticatedPage
        .getByTestId(`${org.name}+${robot.shortname}-set-repo-perms-btn`)
        .click();

      // The page should not crash — verify we're still on the same page
      await expect(
        authenticatedPage.getByText('Add to repository'),
      ).toBeVisible();
    });

    test('permissions kebab should not throw when deleting permission', async ({
      authenticatedPage,
      api,
    }) => {
      // Bug: PermissionsKebab.tsx:27-28
      // Same pattern as RobotAccountKebab: document.getElementById().focus()
      // without null check in onSelect handler.
      //
      // Expected behavior: kebab closes cleanly after selecting action
      // Actual behavior: potential null dereference crash

      const org = await api.organization('permkebab');
      const repo = await api.repository(org.name, 'permrepo');
      const robot = await api.robot(org.name, 'permbot');

      // Add a permission to the repo
      await api.repositoryPermission(
        org.name,
        repo.name,
        'user',
        robot.fullName,
        'read',
      );

      // Navigate to repository settings
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=settings`,
      );

      // Find the permission row for the robot — use fullName for unambiguous match
      const robotRow = authenticatedPage.locator('tr', {
        hasText: robot.fullName,
      });
      await expect(robotRow).toBeVisible();

      // Open the kebab menu for this permission
      const kebab = authenticatedPage.getByTestId(
        `${robot.fullName}-toggle-kebab`,
      );
      await kebab.click();

      // Click "Delete Permission" — triggers onSelect with
      // document.getElementById().focus() without null check
      await authenticatedPage
        .getByRole('menuitem', {name: 'Delete Permission'})
        .click();

      // The page should not crash and the permission should be removed
      await expect(robotRow).not.toBeVisible({timeout: 10000});
    });
  },
);

test.describe(
  'Bug Discovery: Robot Account Repo Permissions Modal',
  {tag: ['@bug-discovery', '@organization']},
  () => {
    test('changing repo permissions should reflect immediately in the UI', async ({
      authenticatedPage,
      api,
    }) => {
      // BUG CONFIRMED: test.fixme() — state mutation prevents immediate UI update
      test.fixme();
      // Bug: AddToRepository.tsx:149-151
      // When updating robot account repository permissions outside the wizard,
      // the code performs a direct state mutation:
      //   const tempItem = updatedRepoPerms;   // alias, NOT copy
      //   delete tempItem[repoName];           // mutates state directly
      //   setUpdatedRepoPerms(tempItem);       // same reference, React may skip
      //
      // Additional bug at line 53: props.repos.sort() mutates parent state.
      // Additional bug at line 216: updateRobotAccountsList() called in render.
      //
      // Expected behavior: permission changes reflect immediately in dropdown
      // Actual behavior: may require extra render cycles or show stale values

      const org = await api.organization('robotperms');
      const repo = await api.repository(org.name, 'permrepo');
      const robot = await api.robot(org.name, 'permbot');

      // Navigate to robot accounts page
      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Robotaccounts`,
      );

      // Open the kebab menu for the robot and click "Set repository permissions"
      const kebab = authenticatedPage.getByTestId(
        `${org.name}+${robot.shortname}-toggle-kebab`,
      );
      await kebab.click();
      await authenticatedPage
        .getByTestId(`${org.name}+${robot.shortname}-set-repo-perms-btn`)
        .click();

      // Wait for the "Add to repository" modal/panel to appear
      await expect(
        authenticatedPage.getByText('Add to repository'),
      ).toBeVisible();

      // Verify the repository appears in the list
      const repoCheckbox = authenticatedPage.getByTestId(
        `checkbox-row-${repo.name}`,
      );
      await expect(repoCheckbox).toBeVisible();

      // Select the repository
      await repoCheckbox.locator('input[type="checkbox"]').check();

      // Open the bulk permissions kebab and set permission to "Write"
      await authenticatedPage.locator('#toggle-bulk-perms-kebab').click();
      await authenticatedPage.getByRole('menuitem', {name: 'Write'}).click();

      // The permission dropdown for this repo should now show "Write"
      // Due to the state mutation bug, this might not update immediately
      const permDropdown = authenticatedPage
        .locator('tr', {hasText: repo.name})
        .locator('[class*="dropdown"]')
        .first();

      // Verify the permission value updated
      await expect(permDropdown).toContainText('Write', {timeout: 5000});
    });
  },
);
