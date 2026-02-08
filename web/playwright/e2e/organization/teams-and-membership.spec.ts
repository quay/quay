import {test, expect, uniqueName, mailpit} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

/**
 * Helper to wait for pagination to show expected count
 * Uses toContainText to verify pagination text appears (avoids visibility issues)
 */
async function expectPaginationCount(
  page: import('@playwright/test').Page,
  count: string,
  timeout = 10000,
) {
  // Wait for the page to contain the pagination text
  await expect(page.locator('body')).toContainText(count, {timeout});
}

test.describe('Teams and Membership', {tag: ['@organization', '@team']}, () => {
  test('team lifecycle: search, create, update role, delete', async ({
    authenticatedPage,
    api,
  }) => {
    // Setup: Create org with a repo and initial team
    const org = await api.organization('lifecycle');
    const repo = await api.repository(org.name, 'testrepo');
    const existingTeam = await api.team(org.name, 'existingteam');

    // Navigate to Teams and Membership tab
    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    // Click Teams tab
    await authenticatedPage.getByTestId('teams-tab').click();

    // === Test 1: Search Filter for Team View ===
    await authenticatedPage
      .getByTestId('teams-view-search')
      .fill(existingTeam.name);
    await expectPaginationCount(authenticatedPage, '1 - 1 of 1');
    await authenticatedPage.getByTestId('teams-view-search').clear();

    // === Test 4: Create a new team via wizard ===
    const newTeamName = uniqueName('newteam').replace(/-/g, '');
    const teamDescription = 'Test team created by Playwright';

    await authenticatedPage.getByTestId('create-new-team-button').click();

    // Create team modal
    await authenticatedPage
      .getByTestId('new-team-name-input')
      .fill(newTeamName);
    await authenticatedPage
      .getByTestId('new-team-description-input')
      .fill(teamDescription);
    await authenticatedPage.getByTestId('create-team-confirm').click();

    // Verify success alert (use .last() to get most recent alert)
    await expect(
      authenticatedPage
        .getByText(`Successfully created new team: ${newTeamName}`)
        .last(),
    ).toBeVisible();

    // Create team wizard - step 1: Name & Description (already filled)
    await expect(
      authenticatedPage.getByTestId('create-team-wizard-form-name'),
    ).toHaveValue(newTeamName);
    await expect(
      authenticatedPage.getByTestId('create-team-wizard-form-description'),
    ).toHaveValue(teamDescription);
    await authenticatedPage.getByTestId('next-btn').click();

    // Step 2: Add to repository
    await authenticatedPage.getByTestId(`checkbox-row-${repo.name}`).click();
    await expect(
      authenticatedPage.getByTestId(`${repo.name}-permission-dropdown-toggle`),
    ).toContainText('Read');
    await authenticatedPage.getByTestId('next-btn').click();

    // Step 3: Add team member
    await authenticatedPage.locator('#search-member-dropdown').click();
    // Use pressSequentially for typeahead inputs that are divs not inputs
    await authenticatedPage
      .locator('#search-member-dropdown-input input')
      .pressSequentially(TEST_USERS.user.username, {delay: 50});
    await authenticatedPage.getByTestId(TEST_USERS.user.username).click();
    await authenticatedPage.getByTestId('next-btn').click();

    // Step 4: Review and Finish
    await expect(
      authenticatedPage.getByTestId(`${newTeamName}-team-name-review`),
    ).toHaveValue(newTeamName);
    await expect(
      authenticatedPage.getByTestId(`${teamDescription}-team-descr-review`),
    ).toHaveValue(teamDescription);
    await expect(
      authenticatedPage.getByTestId('selected-repos-review'),
    ).toHaveValue(repo.name);
    await authenticatedPage.getByTestId('review-and-finish-wizard-btn').click();

    // Verify success alert for adding members
    await expect(
      authenticatedPage.getByText('Successfully added members to team').last(),
    ).toBeVisible();

    // === Test 5: Update team role ===
    // Search for the existing team
    await authenticatedPage
      .getByTestId('teams-view-search')
      .fill(existingTeam.name);
    await expectPaginationCount(authenticatedPage, '1 - 1 of 1');

    // Update team role from Member to Creator
    await authenticatedPage
      .getByTestId(`${existingTeam.name}-team-dropdown-toggle`)
      .click();
    await authenticatedPage.getByTestId(`${existingTeam.name}-Creator`).click();

    // Verify success alert
    await expect(
      authenticatedPage
        .getByText(`Team role updated successfully for: ${existingTeam.name}`)
        .last(),
    ).toBeVisible();

    // === Test 6: Delete team ===
    // Search for the new team we just created to delete it
    await authenticatedPage.getByTestId('teams-view-search').clear();
    await authenticatedPage.getByTestId('teams-view-search').fill(newTeamName);
    await expectPaginationCount(authenticatedPage, '1 - 1 of 1');

    await authenticatedPage.getByTestId(`${newTeamName}-toggle-kebab`).click();
    await authenticatedPage.getByTestId(`${newTeamName}-del-option`).click();
    await authenticatedPage.getByTestId(`${newTeamName}-del-btn`).click();

    // Verify success alert
    await expect(
      authenticatedPage
        .getByText(`Successfully deleted team: ${newTeamName}`)
        .last(),
    ).toBeVisible();
  });

  test('team repository permissions: set and bulk update', async ({
    authenticatedPage,
    api,
  }) => {
    // Setup: Create org with multiple repos and a team
    const org = await api.organization('repoperms');
    const repo1 = await api.repository(org.name, 'repo1');
    await api.repository(org.name, 'repo2'); // Second repo for bulk update test
    const team = await api.team(org.name, 'permteam');

    // Navigate to Teams and Membership tab
    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );
    await authenticatedPage.getByTestId('teams-tab').click();

    // === Test 8: Set repository permissions for a team ===
    await authenticatedPage.getByTestId('teams-view-search').fill(team.name);
    await expectPaginationCount(authenticatedPage, '1 - 1 of 1');

    await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();
    await authenticatedPage
      .getByTestId(`${team.name}-set-repo-perms-option`)
      .click();

    // Search for repo in the modal
    await authenticatedPage
      .locator('#set-repo-perm-for-team-search')
      .fill(repo1.name);
    await expectPaginationCount(authenticatedPage, '1 - 1 of 1');

    // Change permission from None to Write
    await authenticatedPage
      .getByTestId(`${repo1.name}-role-dropdown-toggle`)
      .click();
    await authenticatedPage.getByTestId(`${repo1.name}-Write`).click();
    await authenticatedPage.locator('#update-team-repo-permissions').click();

    // Verify success alert
    await expect(
      authenticatedPage
        .getByText(`Updated repo perm for team: ${team.name} successfully`)
        .last(),
    ).toBeVisible();

    // === Test 9: Bulk update repo permissions ===
    await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();
    await authenticatedPage
      .getByTestId(`${team.name}-set-repo-perms-option`)
      .click();

    // Bulk select all and change role
    await authenticatedPage
      .locator('[name="add-repository-bulk-select"]')
      .click();
    await authenticatedPage.locator('#toggle-bulk-perms-kebab').click();
    // Click "Write" option in the dropdown (it's a list item, not a menuitem)
    await authenticatedPage.getByText('Write', {exact: true}).first().click();
    await authenticatedPage.locator('#update-team-repo-permissions').click();

    // Verify success alert
    await expect(
      authenticatedPage
        .getByText(`Updated repo perm for team: ${team.name} successfully`)
        .last(),
    ).toBeVisible();
  });

  test('team navigation and description edit', async ({
    authenticatedPage,
    api,
  }) => {
    // Setup
    const org = await api.organization('teamnav');
    const team = await api.team(org.name, 'navteam');
    const newDescription = 'Updated description for testing';

    // Navigate to Teams and Membership tab
    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );
    await authenticatedPage.getByTestId('teams-tab').click();

    // Search for team
    await authenticatedPage.getByTestId('teams-view-search').fill(team.name);
    await expectPaginationCount(authenticatedPage, '1 - 1 of 1');

    // Click team name to navigate to team management page
    await authenticatedPage.getByRole('link', {name: team.name}).click();
    await expect(authenticatedPage).toHaveURL(new RegExp(`teams/${team.name}`));

    // Verify team name is displayed
    await expect(authenticatedPage.getByTestId('teamname-title')).toContainText(
      team.name,
    );

    // Edit team description
    await authenticatedPage.getByTestId('edit-team-description-btn').click();
    await authenticatedPage
      .getByTestId('team-description-text-area')
      .fill(newDescription);
    await authenticatedPage.getByTestId('save-team-description-btn').click();

    // Verify success alert
    await expect(
      authenticatedPage
        .getByText(`Successfully updated team:${team.name} description`)
        .last(),
    ).toBeVisible();

    // Verify description is updated
    await expect(
      authenticatedPage.getByTestId('team-description-text'),
    ).toContainText(newDescription);
  });

  test('members view: search and filter', async ({authenticatedPage, api}) => {
    // Setup: Create org, team, and add a member
    const org = await api.organization('members');
    const team = await api.team(org.name, 'memberteam');
    await api.teamMember(org.name, team.name, TEST_USERS.user.username);

    // Navigate to Teams and Membership tab
    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    // Click Members tab
    await authenticatedPage.getByTestId('members-tab').click();

    // Search for member
    await authenticatedPage
      .getByTestId('members-view-search')
      .fill(TEST_USERS.user.username);
    await expectPaginationCount(authenticatedPage, '1 - 1 of 1');

    // Clear search
    await authenticatedPage.getByTestId('members-view-search').clear();
  });

  test('collaborators view: search and delete', async ({
    authenticatedPage,
    api,
    superuserApi,
  }) => {
    // Setup: Create org, repo, and give a user direct permission (creating a collaborator)
    const org = await api.organization('collabs');
    const repo = await api.repository(org.name, 'collabrepo');
    const collaborator = await superuserApi.user('collaborator');

    // Give user direct permission on repo (this makes them a collaborator)
    await api.repositoryPermission(
      org.name,
      repo.name,
      'user',
      collaborator.username,
      'read',
    );

    // Navigate to Teams and Membership tab
    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    // Click Collaborators tab
    await authenticatedPage.getByTestId('collaborators-tab').click();

    // Search for collaborator
    await authenticatedPage
      .getByTestId('collaborators-view-search')
      .fill(collaborator.username);
    await expectPaginationCount(authenticatedPage, '1 - 1 of 1');

    // Delete collaborator
    await authenticatedPage
      .getByTestId(`${collaborator.username}-del-icon`)
      .click();
    await authenticatedPage
      .getByTestId(`${collaborator.username}-del-btn`)
      .click();

    // Verify success alert
    await expect(
      authenticatedPage.getByText('Successfully deleted collaborator').last(),
    ).toBeVisible();
  });

  test('non-admin user cannot edit teams', async ({
    readonlyPage,
    api,
    quayConfig,
  }) => {
    // Setup: Create org owned by testuser with a team
    const org = await api.organization('readonly');
    const team = await api.team(org.name, 'viewonly');

    // Create a robot account in the team for the member count
    const robot = await api.robot(org.name, 'testrobot');
    await api.teamMember(org.name, team.name, robot.fullName);

    // Add readonly user as team member (triggers invitation email if mailing enabled)
    await api.teamMember(org.name, team.name, TEST_USERS.readonly.username);

    // If FEATURE_MAILING is enabled, wait for and confirm the team invitation email
    const mailingEnabled = quayConfig?.features?.MAILING === true;
    if (mailingEnabled) {
      const confirmLink = await mailpit.waitForEmail(
        (msg) =>
          msg.To.some((to) => to.Address === TEST_USERS.readonly.email) &&
          (msg.Subject.toLowerCase().includes('invite') ||
            msg.Subject.toLowerCase().includes('team') ||
            msg.Subject.toLowerCase().includes('confirm')),
        15000,
      );
      if (confirmLink) {
        const link = await mailpit.extractLink(confirmLink.ID);
        if (link) {
          // Visit the confirmation link to accept team membership
          await readonlyPage.goto(link);
          await readonlyPage.waitForLoadState('networkidle');
        }
      }
    }

    // Navigate as readonly user (who is a team member, not org admin)
    await readonlyPage.goto(`/organization/${org.name}?tab=Teamsandmembership`);
    await readonlyPage.getByTestId('teams-tab').click();

    // Search for team
    await readonlyPage.getByTestId('teams-view-search').fill(team.name);
    await expectPaginationCount(readonlyPage, '1 - 1 of 1');

    // Verify create new team button is not visible for non-admin
    await expect(
      readonlyPage.getByTestId('create-new-team-button'),
    ).not.toBeVisible();

    // Verify team role dropdown is disabled for non-admin
    await expect(
      readonlyPage.getByTestId(`${team.name}-team-dropdown-toggle`),
    ).toBeDisabled();

    // Verify kebab option is not visible for non-admin
    await expect(
      readonlyPage.getByTestId(`${team.name}-toggle-kebab`),
    ).not.toBeVisible();

    // Navigate to team management page via member count link
    // Click the link inside the cell (data-testid is on the Td, not the Link)
    await readonlyPage
      .getByTestId(`member-count-for-${team.name}`)
      .getByRole('link')
      .click();
    await expect(readonlyPage).toHaveURL(new RegExp(`teams/${team.name}`));

    // Verify editable options are not visible for non-admin
    await expect(
      readonlyPage.getByTestId('add-new-member-button'),
    ).not.toBeVisible();
    await expect(
      readonlyPage.getByTestId('edit-team-description-btn'),
    ).not.toBeVisible();
    await expect(
      readonlyPage.getByTestId(`${robot.fullName}-delete-icon`),
    ).not.toBeVisible();
  });
});

test.describe(
  'Team syncing',
  {
    tag: [
      '@organization',
      '@team',
      '@skip',
      '@feature:TEAM_SYNCING',
      '@auth:OIDC',
      '@auth:LDAP',
    ],
  },
  () => {
    // TODO: Enable when OIDC/LDAP backend is configured
    // test('shows sync icon for synchronized teams', async ({
    //   authenticatedPage,
    //   api,
    // }) => {
    //   const org = await api.organization('teamsync');
    //   await api.team(org.name, 'syncteam', {synced: true});
    //
    //   await authenticatedPage.goto(
    //     `/organization/${org.name}?tab=Teamsandmembership`,
    //   );
    //   await authenticatedPage.getByTestId('teams-tab').click();
    //
    //   await expect(
    //     authenticatedPage.getByTestId('teams-view-search'),
    //   ).toBeVisible();
    //
    //   // When a synced team exists, the sync icon should be visible
    //   await expect(authenticatedPage.getByTestId('sync-icon')).toBeVisible();
    // });

    test.skip('shows sync icon for synchronized teams', async () => {
      // Placeholder - requires OIDC/LDAP backend configuration
    });
  },
);
