import {test, expect, getTestUsers} from '../../fixtures';
import {RawApiClient} from '../../utils/api';
import {API_URL} from '../../utils/config';
import type {Page} from '@playwright/test';

async function navigateToManageTeamMembers(
  page: Page,
  orgName: string,
  teamName: string,
) {
  await page.goto(`/organization/${orgName}?tab=Teamsandmembership`);
  await page.locator('#Teams').click();

  await page.locator('#teams-view-search').fill(teamName);
  await expect(
    page.locator('.pf-v6-c-pagination__total-items').first(),
  ).toContainText('1 - 1 of 1', {timeout: 15000});

  await page.getByTestId(`${teamName}-toggle-kebab`).click();
  await page.getByTestId(`${teamName}-manage-team-member-option`).click();
}

test.describe('Manage Team Members', {tag: ['@organization']}, () => {
  test('can search for member', async ({
    authenticatedPage,
    api,
    quayConfig,
  }) => {
    const users = getTestUsers(quayConfig);
    const org = await api.organization('testorg');
    const team = await api.team(org.name, 'searchteam');
    await api.teamMember(org.name, team.name, users.user.username);

    await navigateToManageTeamMembers(authenticatedPage, org.name, team.name);

    await expect(authenticatedPage).toHaveURL(
      new RegExp(`teams/${team.name}\\?tab=Teamsandmembership`),
    );
    await expect(
      authenticatedPage.locator('[data-label="Team member"]'),
    ).toContainText(users.user.username);
  });

  test('team member filter toggle', async ({
    authenticatedPage,
    api,
    quayConfig,
  }) => {
    const users = getTestUsers(quayConfig);
    const org = await api.organization('testorg');
    const team = await api.team(org.name, 'filterteam');
    const robot = await api.robot(org.name, 'filterbot');
    await api.teamMember(org.name, team.name, users.user.username);
    await api.teamMember(org.name, team.name, robot.fullName);

    await navigateToManageTeamMembers(authenticatedPage, org.name, team.name);

    await authenticatedPage.getByTestId('Team Member').click();

    const searchInput = authenticatedPage.locator('#team-member-search-input');
    const paginationInfo = authenticatedPage
      .locator('.pf-v6-c-pagination__total-items')
      .first();

    // Verify team member is shown
    await searchInput.fill(users.user.username);
    await expect(paginationInfo).toContainText('1 - 1 of 1');

    // Verify robot account is not shown
    await searchInput.fill(robot.fullName);
    await expect(paginationInfo).toContainText('0 - 0 of 0');
  });

  test('robot accounts filter toggle', async ({
    authenticatedPage,
    api,
    quayConfig,
  }) => {
    const users = getTestUsers(quayConfig);
    const org = await api.organization('testorg');
    const team = await api.team(org.name, 'robotfilter');
    const robot = await api.robot(org.name, 'robotbot');
    await api.teamMember(org.name, team.name, users.user.username);
    await api.teamMember(org.name, team.name, robot.fullName);

    await navigateToManageTeamMembers(authenticatedPage, org.name, team.name);

    await authenticatedPage.getByTestId('Robot Accounts').click();

    const searchInput = authenticatedPage.locator('#team-member-search-input');
    const paginationInfo = authenticatedPage
      .locator('.pf-v6-c-pagination__total-items')
      .first();

    // Verify robot account is shown
    await searchInput.fill(robot.fullName);
    await expect(paginationInfo).toContainText('1 - 1 of 1');

    // Verify team member is not shown
    await searchInput.fill(users.user.username);
    await expect(paginationInfo).toContainText('0 - 0 of 0');
  });

  test('can update team description', async ({authenticatedPage, api}) => {
    const org = await api.organization('testorg');
    const team = await api.team(org.name, 'descrteam');
    const teamDescription = 'Updated team description for testing';

    await navigateToManageTeamMembers(authenticatedPage, org.name, team.name);

    await authenticatedPage.getByTestId('edit-team-description-btn').click();
    await authenticatedPage
      .getByTestId('team-description-text-area')
      .fill(teamDescription);
    await authenticatedPage.getByTestId('save-team-description-btn').click();

    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully updated team:${team.name} description`);
    await expect(
      authenticatedPage.getByTestId('team-description-text'),
    ).toContainText(teamDescription);
  });

  test('can delete robot from team', async ({authenticatedPage, api}) => {
    const org = await api.organization('testorg');
    const team = await api.team(org.name, 'delrobotteam');
    const robot = await api.robot(org.name, 'delbot');
    await api.teamMember(org.name, team.name, robot.fullName);

    await navigateToManageTeamMembers(authenticatedPage, org.name, team.name);

    await authenticatedPage
      .getByTestId(`${robot.fullName}-delete-icon`)
      .click();
    await authenticatedPage.getByTestId(`${robot.fullName}-del-btn`).click();

    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully deleted team member: ${robot.fullName}`);
  });

  test('can add new robot via wizard', async ({authenticatedPage, api}) => {
    const org = await api.organization('testorg');
    const team = await api.team(org.name, 'addrobotteam');
    const repo = await api.repository(org.name, 'wizardrepo');
    const newRobotName = `testbot${Date.now()}`.substring(0, 20);
    const newRobotDescription = 'robot created via wizard';

    await navigateToManageTeamMembers(authenticatedPage, org.name, team.name);

    await authenticatedPage.getByTestId('add-new-member-button').click();

    await authenticatedPage.locator('#repository-creator-dropdown').click();
    await authenticatedPage.getByTestId('create-new-robot-accnt-btn').click();

    // Step 1: Name & Description
    await authenticatedPage
      .getByTestId('robot-wizard-form-name')
      .fill(newRobotName);
    await authenticatedPage
      .getByTestId('robot-wizard-form-description')
      .fill(newRobotDescription);
    await authenticatedPage.getByTestId('next-btn').click();

    // Step 2: Add to team (skip)
    await authenticatedPage.getByTestId('next-btn').click();

    // Step 3: Add to repository
    await authenticatedPage.getByTestId(`checkbox-row-${repo.name}`).click();
    await authenticatedPage.getByTestId('next-btn').click();

    // Step 4: Default permissions
    await expect(authenticatedPage.getByTestId('applied-to-input')).toHaveValue(
      newRobotName,
    );
    await authenticatedPage.getByTestId('next-btn').click();

    // Step 5: Review and Finish
    await authenticatedPage.getByTestId('create-robot-submit').click();

    // Verify robot is auto-selected in dropdown
    await expect(
      authenticatedPage.locator('#repository-creator-dropdown input'),
    ).toHaveValue(`${org.name}+${newRobotName}`);

    // Submit add member
    await authenticatedPage.getByTestId('add-new-member-submit-btn').click();

    // Verify success
    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully added "${org.name}+${newRobotName}" to team`);
    await expect(
      authenticatedPage.getByTestId(`${org.name}+${newRobotName}`),
    ).toContainText(`${org.name}+${newRobotName}`);
  });

  test(
    'pagination works with more than 20 members',
    {tag: '@superuser'},
    async ({authenticatedPage, api}) => {
      const org = await api.organization('testorg');
      const team = await api.team(org.name, 'paginationteam');

      // Robots count as team members and need no user accounts, so this
      // runs under any auth type.
      for (let i = 0; i < 25; i++) {
        const robot = await api.robot(org.name, `pgbot${i}`);
        await api.teamMember(org.name, team.name, robot.fullName);
      }

      await navigateToManageTeamMembers(authenticatedPage, org.name, team.name);

      const paginationInfo = authenticatedPage
        .locator('.pf-v6-c-pagination__total-items')
        .first();

      // Verify pagination shows correct total (25 members)
      await expect(paginationInfo).toContainText('of 25', {timeout: 15000});
      await expect(paginationInfo).toContainText('1 - 20');

      // Verify next page button is enabled and clickable
      const nextPageBtn = authenticatedPage
        .locator('#team-members-toolbar')
        .getByRole('button', {name: 'Go to next page'});
      await expect(nextPageBtn).toBeEnabled();

      // Navigate to page 2
      await nextPageBtn.click();

      // Verify page 2 shows remaining members
      await expect(paginationInfo).toContainText('21 - 25 of 25');

      // Verify previous page button is enabled on page 2
      const prevPageBtn = authenticatedPage
        .locator('#team-members-toolbar')
        .getByRole('button', {name: 'Go to previous page'});
      await expect(prevPageBtn).toBeEnabled();
    },
  );

  test('can add user to team', async ({authenticatedPage, api, quayConfig}) => {
    const org = await api.organization('testorg');
    const team = await api.team(org.name, 'adduserteam');
    const userToAdd = getTestUsers(quayConfig).admin.username;

    await navigateToManageTeamMembers(authenticatedPage, org.name, team.name);

    await authenticatedPage.getByTestId('add-new-member-button').click();

    await authenticatedPage.locator('#repository-creator-dropdown').click();
    await authenticatedPage
      .locator('#repository-creator-dropdown input')
      .fill(userToAdd);
    await authenticatedPage.getByTestId(userToAdd).click();

    // Verify user is selected in dropdown
    await expect(
      authenticatedPage.locator('#repository-creator-dropdown input'),
    ).toHaveValue(userToAdd);

    // Submit add member
    await authenticatedPage.getByTestId('add-new-member-submit-btn').click();

    // Verify success
    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully added "${userToAdd}" to team`);
    await expect(authenticatedPage.getByTestId(userToAdd)).toContainText(
      userToAdd,
    );
  });
});

test.describe(
  'Team invitations',
  {
    tag: [
      '@organization',
      '@auth:Database',
      '@feature:MAILING',
      '@feature:REQUIRE_TEAM_INVITE',
      '@superuser',
    ],
  },
  () => {
    test('invite is bound to its user, single use, and can be declined', async ({
      api,
      userClient,
      freshUser,
      request,
    }) => {
      const org = await api.organization('invite');
      const joinTeam = await api.team(org.name, 'join');
      const declineTeam = await api.team(org.name, 'decline');
      const invitee = freshUser.user.username;

      for (const team of [joinTeam, declineTeam]) {
        const r = await userClient.put(
          `/api/v1/organization/${org.name}/team/${team.name}/members/${invitee}`,
        );
        expect(r.status()).toBe(200);
        expect((await r.json()).invited).toBe(true);
      }

      const inviteeClient = new RawApiClient(request, API_URL);
      await inviteeClient.signIn(invitee, freshUser.user.password);
      const notifications = await inviteeClient.get(
        '/api/v1/user/notifications?limit=20',
      );
      expect(notifications.status()).toBe(200);
      const codes = new Map<string, string>(
        (
          (await notifications.json()).notifications as Array<{
            kind: string;
            metadata: {org?: string; team?: string; code?: string};
          }>
        )
          .filter(
            (n) => n.kind === 'org_team_invite' && n.metadata.org === org.name,
          )
          .map((n) => [n.metadata.team, n.metadata.code]),
      );
      const joinCode = codes.get(joinTeam.name);
      const declineCode = codes.get(declineTeam.name);
      expect(joinCode).toBeTruthy();
      expect(declineCode).toBeTruthy();

      const members = async (teamName: string) => {
        const r = await userClient.get(
          `/api/v1/organization/${org.name}/team/${teamName}/members?includePending=true`,
        );
        expect(r.status()).toBe(200);
        return (
          (await r.json()).members as Array<{name: string; invited: boolean}>
        ).map(({name, invited}) => ({name, invited}));
      };

      const otherUser = await userClient.put(`/api/v1/teaminvite/${joinCode}`);
      expect(otherUser.status()).toBe(400);
      expect((await otherUser.json()).message).toContain(
        `intended for user "${invitee}"`,
      );
      expect(await members(joinTeam.name)).toEqual([
        {name: invitee, invited: true},
      ]);

      const decline = await inviteeClient.delete(
        `/api/v1/teaminvite/${declineCode}`,
      );
      expect(decline.status()).toBe(204);
      expect(await members(declineTeam.name)).toEqual([]);

      const accept = await inviteeClient.put(`/api/v1/teaminvite/${joinCode}`);
      expect(accept.status()).toBe(200);
      expect(await accept.json()).toEqual({org: org.name, team: joinTeam.name});

      const reuse = await inviteeClient.put(`/api/v1/teaminvite/${joinCode}`);
      expect(reuse.status()).toBe(400);

      expect(await members(joinTeam.name)).toEqual([
        {name: invitee, invited: false},
      ]);
      // Accepting confirms every pending invite in the org, so a declined
      // invite that survived would surface as a membership here.
      expect(await members(declineTeam.name)).toEqual([]);
    });
  },
);
