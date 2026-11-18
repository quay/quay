import {test, expect, uniqueName, getTestUsers} from '../../fixtures';
import type {Page} from '@playwright/test';

async function navigateToTeamsTab(page: Page, orgName: string) {
  await page.goto(`/organization/${orgName}?tab=Teamsandmembership`);
  await page.locator('#Teams').click();
}

async function searchForTeam(page: Page, teamName: string) {
  await page.locator('#teams-view-search').fill(teamName);
  await expect(
    page.locator('.pf-v6-c-pagination__total-items').first(),
  ).toContainText('1 - 1 of 1', {timeout: 15000});
}

test.describe('Teams and Membership', {tag: ['@organization']}, () => {
  test('team search filter', async ({authenticatedPage, api}) => {
    const org = await api.organization('tmorg');
    const team = await api.team(org.name, 'searchteam');

    await navigateToTeamsTab(authenticatedPage, org.name);

    await searchForTeam(authenticatedPage, team.name);
  });

  test(
    'search resets pagination to page 1',
    {tag: ['@PROJQUAY-14330']},
    async ({authenticatedPage, api}) => {
      const org = await api.organization('tmorg');
      await Promise.all(
        Array.from({length: 21}, () => api.team(org.name, 'pgteam')),
      );
      const pagination = authenticatedPage
        .locator('.pf-v6-c-pagination__total-items')
        .first();

      await navigateToTeamsTab(authenticatedPage, org.name);
      await authenticatedPage.getByTestId('teams-view-search').fill('pgteam');
      await expect(pagination).toHaveText('1 - 20 of 21', {timeout: 15000});

      const page1TeamName = (
        await authenticatedPage
          .getByRole('link', {name: /^pgteam-/})
          .first()
          .textContent()
      ).trim();

      await authenticatedPage
        .getByRole('button', {name: 'Go to next page'})
        .first()
        .click();
      await expect(pagination).toHaveText('21 - 21 of 21', {timeout: 15000});

      await authenticatedPage
        .getByTestId('teams-view-search')
        .fill(page1TeamName);

      await expect(pagination).toHaveText('1 - 1 of 1', {timeout: 15000});
      await expect(
        authenticatedPage.getByRole('link', {name: page1TeamName, exact: true}),
      ).toBeVisible();
    },
  );

  test('member search filter', async ({authenticatedPage, api, quayConfig}) => {
    const users = getTestUsers(quayConfig);
    const org = await api.organization('tmorg');
    const memberTeam = await api.team(org.name, 'memberteam');
    await api.teamMember(org.name, memberTeam.name, users.user.username);

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );
    await authenticatedPage.locator('#Members').click();

    await authenticatedPage
      .locator('#members-view-search')
      .fill(users.user.username);
    await expect(
      authenticatedPage.locator('.pf-v6-c-pagination__total-items').first(),
    ).toContainText('1 - 1 of 1', {timeout: 15000});
  });

  test('collaborator search filter', async ({
    authenticatedPage,
    api,
    quayConfig,
  }) => {
    const users = getTestUsers(quayConfig);
    const org = await api.organization('tmorg');
    const repo = await api.repository(org.name, 'collabsearch');
    await api.repositoryPermission(
      org.name,
      repo.name,
      'user',
      users.readonly.username,
      'read',
    );

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );
    await authenticatedPage.locator('#Collaborators').click();

    await authenticatedPage
      .locator('#collaborators-view-search')
      .fill(users.readonly.username);
    await expect(
      authenticatedPage.locator('.pf-v6-c-pagination__total-items').first(),
    ).toContainText('1 - 1 of 1', {timeout: 15000});
  });

  test('create team via wizard', async ({
    authenticatedPage,
    api,
    quayConfig,
  }) => {
    const users = getTestUsers(quayConfig);
    const org = await api.organization('tmorg');
    const repo = await api.repository(org.name, 'wizardrepo');
    const teamName = uniqueName('wizteam');
    const teamDescription = 'team created by playwright wizard test';

    await navigateToTeamsTab(authenticatedPage, org.name);

    // Open create team modal
    await authenticatedPage.getByTestId('create-new-team-button').click();
    await authenticatedPage.getByTestId('new-team-name-input').fill(teamName);
    await authenticatedPage
      .getByTestId('new-team-description-input')
      .fill(teamDescription);
    await authenticatedPage.getByTestId('create-team-confirm').click();

    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully created new team: ${teamName}`);

    // Wizard Step 1: Name & Description (pre-filled)
    await expect(
      authenticatedPage.getByTestId('create-team-wizard-form-name'),
    ).toHaveValue(teamName);
    await expect(
      authenticatedPage.getByTestId('create-team-wizard-form-description'),
    ).toHaveValue(teamDescription);
    await authenticatedPage.getByTestId('next-btn').click();

    // Wizard Step 2: Add to repository
    const repoRow = authenticatedPage.getByTestId(`checkbox-row-${repo.name}`);
    await repoRow.getByRole('checkbox').check();
    await expect(
      authenticatedPage.getByTestId(`${repo.name}-permission-dropdown-toggle`),
    ).toContainText('Read');
    await authenticatedPage.getByTestId('next-btn').click();

    // Wizard Step 3: Add team member
    await authenticatedPage.locator('#search-member-dropdown').click();
    await authenticatedPage
      .locator('#search-member-dropdown-input input')
      .fill(users.admin.username);
    await authenticatedPage.getByTestId(users.admin.username).click();
    await authenticatedPage.getByTestId('next-btn').click();

    // Wizard Step 4: Review and Finish
    await expect(
      authenticatedPage.getByTestId(`${teamName}-team-name-review`),
    ).toHaveValue(teamName);
    await expect(
      authenticatedPage.getByTestId('selected-repos-review'),
    ).toHaveValue(repo.name);
    await expect(
      authenticatedPage.getByTestId('selected-team-members-review'),
    ).toHaveValue(users.admin.username);
    await authenticatedPage.getByTestId('review-and-finish-wizard-btn').click();

    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText('Successfully added members to team');

    // Verify new team appears in search
    await authenticatedPage.locator('#teams-view-search').fill(teamName);
    await expect(
      authenticatedPage.locator('.pf-v6-c-pagination__total-items').first(),
    ).toContainText('1 - 1 of 1', {timeout: 15000});
  });

  test('team wizard review accepts empty optional repositories and members', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('tmorg');
    const teamName = uniqueName('emptyteam');

    await navigateToTeamsTab(authenticatedPage, org.name);

    await authenticatedPage.getByTestId('create-new-team-button').click();
    await authenticatedPage.getByTestId('new-team-name-input').fill(teamName);
    await authenticatedPage.getByTestId('create-team-confirm').click();

    await expect(
      authenticatedPage
        .getByText(`Successfully created new team: ${teamName}`)
        .last(),
    ).toBeVisible();

    await authenticatedPage.getByTestId('next-btn').click();
    await authenticatedPage.getByTestId('next-btn').click();
    await authenticatedPage.getByTestId('next-btn').click();

    await expect(
      authenticatedPage.getByTestId(`${teamName}-team-name-review`),
    ).toHaveValue(teamName);
    await expect(
      authenticatedPage.getByTestId('selected-repos-review'),
    ).toHaveValue('');
    await expect(
      authenticatedPage.getByTestId('selected-team-members-review'),
    ).toHaveValue('');
    const finishButton = authenticatedPage.getByTestId(
      'review-and-finish-wizard-btn',
    );
    await finishButton.click();
    await expect(finishButton).toBeHidden();

    await searchForTeam(authenticatedPage, teamName);
  });

  test('update team role', async ({authenticatedPage, api}) => {
    const org = await api.organization('tmorg');
    const team = await api.team(org.name, 'roleteam', 'member');

    await navigateToTeamsTab(authenticatedPage, org.name);
    await searchForTeam(authenticatedPage, team.name);

    await authenticatedPage
      .getByTestId(`${team.name}-team-dropdown-toggle`)
      .click();
    await authenticatedPage.getByTestId(`${team.name}-Creator`).click();

    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText(`Team role updated successfully for: ${team.name}`);
  });

  test('delete team', async ({authenticatedPage, api}) => {
    const org = await api.organization('tmorg');
    const team = await api.team(org.name, 'delteam');

    await navigateToTeamsTab(authenticatedPage, org.name);
    await searchForTeam(authenticatedPage, team.name);

    await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();
    await authenticatedPage.getByTestId(`${team.name}-del-option`).click();
    await authenticatedPage.getByTestId(`${team.name}-del-btn`).click();

    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully deleted team: ${team.name}`);
  });

  test('delete collaborator', async ({authenticatedPage, api, quayConfig}) => {
    const users = getTestUsers(quayConfig);
    const org = await api.organization('tmorg');
    const repo = await api.repository(org.name, 'delcollabsearch');
    await api.repositoryPermission(
      org.name,
      repo.name,
      'user',
      users.readonly.username,
      'read',
    );

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );
    await authenticatedPage.locator('#Collaborators').click();

    await authenticatedPage
      .getByTestId(`${users.readonly.username}-del-icon`)
      .click();
    await authenticatedPage
      .getByTestId(`${users.readonly.username}-del-btn`)
      .click();

    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText('Successfully deleted collaborator');
  });

  test('set repository permissions for team', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('tmorg');
    const team = await api.team(org.name, 'repopermteam');
    const repo = await api.repository(org.name, 'repoperm');

    await navigateToTeamsTab(authenticatedPage, org.name);
    await searchForTeam(authenticatedPage, team.name);

    await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();
    await authenticatedPage
      .getByTestId(`${team.name}-set-repo-perms-option`)
      .click();

    // Search for repo in modal
    const repoPermissionsDialog = authenticatedPage.getByRole('dialog');
    await repoPermissionsDialog
      .locator('#set-repo-perm-for-team-search')
      .fill(repo.name);
    await expect(
      repoPermissionsDialog.locator('.pf-v6-c-pagination__total-items'),
    ).toContainText('1 - 1 of 1', {timeout: 15000});

    // Change permission to Write
    await authenticatedPage
      .getByTestId(`${repo.name}-role-dropdown-toggle`)
      .click();
    await authenticatedPage.getByTestId(`${repo.name}-Write`).click();
    await authenticatedPage.locator('#update-team-repo-permissions').click();

    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText(`Updated repo perm for team: ${team.name} successfully`);
  });

  test(
    'set repository permissions search resets pagination to page 1',
    {tag: ['@PROJQUAY-14330']},
    async ({authenticatedPage, api}) => {
      const org = await api.organization('tmorg');
      const team = await api.team(org.name, 'pgpermteam');
      await Promise.all(
        Array.from({length: 21}, () => api.repository(org.name, 'pgperm')),
      );

      await navigateToTeamsTab(authenticatedPage, org.name);
      await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();
      await authenticatedPage
        .getByTestId(`${team.name}-set-repo-perms-option`)
        .click();

      const dialog = authenticatedPage.getByRole('dialog');
      const pagination = dialog
        .locator('.pf-v6-c-pagination__total-items')
        .first();
      await expect(pagination).toHaveText('1 - 20 of 21', {timeout: 15000});

      const repoNameCells = dialog.getByRole('gridcell', {name: /^pgperm-/});
      const page1RepoName = (await repoNameCells.first().textContent()).trim();

      await dialog
        .getByRole('button', {name: 'Go to next page'})
        .first()
        .click();
      await expect(pagination).toHaveText('21 - 21 of 21');

      await dialog
        .getByTestId('set-repo-perm-for-team-search')
        .fill(page1RepoName);

      await expect(pagination).toHaveText('1 - 1 of 1');
      await expect(repoNameCells).toHaveText([page1RepoName]);
    },
  );

  test('bulk update repository permissions for team', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('tmorg');
    const team = await api.team(org.name, 'bulkpermteam');
    await api.repository(org.name, 'bulkperm');

    await navigateToTeamsTab(authenticatedPage, org.name);
    await searchForTeam(authenticatedPage, team.name);

    await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();
    await authenticatedPage
      .getByTestId(`${team.name}-set-repo-perms-option`)
      .click();

    // Bulk select all repos and change role via kebab
    await authenticatedPage
      .locator('[name="add-repository-bulk-select"]')
      .click();
    await authenticatedPage.locator('#toggle-bulk-perms-kebab').click();
    await authenticatedPage.getByTestId('bulk-perm-Write').click();
    await authenticatedPage.locator('#update-team-repo-permissions').click();

    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText(`Updated repo perm for team: ${team.name} successfully`);
  });

  test('navigate to team management page', async ({authenticatedPage, api}) => {
    const org = await api.organization('tmorg');
    const team = await api.team(org.name, 'navteam');

    await navigateToTeamsTab(authenticatedPage, org.name);
    await searchForTeam(authenticatedPage, team.name);

    // Click team name link
    await authenticatedPage
      .locator('td')
      .filter({hasText: team.name})
      .getByRole('link', {name: team.name})
      .click();

    await expect(authenticatedPage).toHaveURL(
      (url) => url.pathname === `/organization/${org.name}/teams/${team.name}`,
    );
    await expect(authenticatedPage.getByTestId('teamname-title')).toContainText(
      team.name,
    );
  });

  // Org-name keyword cases that break getTeamMemberPath when domainRoute's
  // organization branch is active (current path is /organization/...).
  // overview/repository/signin substrings on this path do not exercise those
  // regex branches — see repository-list coverage for the repository branch.
  const keywordOrgPrefixes = [
    'testorganization',
    'organization',
    'organizationtest2',
  ] as const;

  for (const orgPrefix of keywordOrgPrefixes) {
    test(
      `team and members links stay correct for org name prefix "${orgPrefix}"`,
      {tag: ['@PROJQUAY-11202']},
      async ({authenticatedPage, api, quayConfig}) => {
        const users = getTestUsers(quayConfig);
        const org = await api.organization(orgPrefix);
        const team = await api.team(org.name, 'keywordnav');
        await api.teamMember(org.name, team.name, users.user.username);

        const expectedTeamPath = `/organization/${org.name}/teams/${team.name}`;

        async function clickTeamLinkAndAssertPath(
          link: ReturnType<typeof authenticatedPage.getByRole>,
        ) {
          const href = await link.getAttribute('href');
          expect(href, `malformed team link href: ${href}`).toContain(
            expectedTeamPath,
          );
          expect(href).not.toContain(`/organization/${org.name}/organization/`);

          await link.click();

          await expect(authenticatedPage).toHaveURL(
            (url) => url.pathname === expectedTeamPath,
          );
          await expect(
            authenticatedPage.getByTestId('teamname-title'),
          ).toContainText(team.name);
        }

        // Teams view
        await navigateToTeamsTab(authenticatedPage, org.name);
        await searchForTeam(authenticatedPage, team.name);
        await clickTeamLinkAndAssertPath(
          authenticatedPage.getByRole('link', {name: team.name}),
        );

        // Members view
        await authenticatedPage.goto(
          `/organization/${org.name}?tab=Teamsandmembership`,
        );
        await authenticatedPage
          .getByRole('button', {name: 'Members View'})
          .click();
        await authenticatedPage
          .getByTestId('members-view-search')
          .fill(users.user.username);
        await expect(
          authenticatedPage.locator('.pf-v6-c-pagination__total-items').first(),
        ).toContainText('1 - 1 of 1', {timeout: 15000});

        await clickTeamLinkAndAssertPath(
          authenticatedPage.getByRole('link', {name: team.name}),
        );
      },
    );
  }
});
