/**
 * Repository Features API Tests
 *
 * Covers permissions, collaborators, teams, notifications, robot accounts,
 * robot federation, default permissions (prototypes), and repository state
 * changes. Each test.describe block is self-contained with its own setup
 * and auto-cleanup via TestApi fixtures.
 */

import {test, expect, uniqueName} from '../../fixtures';

test.describe(
  'Repository Features API',
  {tag: ['@api', '@smoke', '@auth:Database']},
  () => {
    // ========================================================================
    // Permissions
    // ========================================================================

    test.describe('Permissions', () => {
      test('add write permission, update to admin, then remove', async ({
        superuserApi,
        adminClient,
      }) => {
        const org = await superuserApi.organization();
        const repo = await superuserApi.repository(org.name);
        const user = await superuserApi.user();

        // Add write permission
        const addWrite = await adminClient.put(
          `/api/v1/repository/${org.name}/${repo.name}/permissions/user/${user.username}`,
          {role: 'write'},
        );
        expect(addWrite.status()).toBe(200);
        const addWriteBody = await addWrite.json();
        expect(addWriteBody.role).toBe('write');
        expect(addWriteBody.name).toBe(user.username);

        // Update to admin
        const updateAdmin = await adminClient.put(
          `/api/v1/repository/${org.name}/${repo.name}/permissions/user/${user.username}`,
          {role: 'admin'},
        );
        expect(updateAdmin.status()).toBe(200);
        const updateAdminBody = await updateAdmin.json();
        expect(updateAdminBody.role).toBe('admin');
        expect(updateAdminBody.name).toBe(user.username);

        // Remove permission
        const remove = await adminClient.delete(
          `/api/v1/repository/${org.name}/${repo.name}/permissions/user/${user.username}`,
        );
        expect(remove.status()).toBe(204);
      });
    });

    // ========================================================================
    // Collaborators
    // ========================================================================

    test.describe('Collaborators', () => {
      test('list collaborators under organization', async ({
        superuserApi,
        adminClient,
      }) => {
        const org = await superuserApi.organization();
        const repo = await superuserApi.repository(org.name);
        const user = await superuserApi.user();

        // Add the user as a collaborator with write permission
        const addPerm = await adminClient.put(
          `/api/v1/repository/${org.name}/${repo.name}/permissions/user/${user.username}`,
          {role: 'write'},
        );
        expect(addPerm.status()).toBe(200);

        // List collaborators
        const list = await adminClient.get(
          `/api/v1/organization/${org.name}/collaborators`,
        );
        expect(list.status()).toBe(200);
        const body = await list.json();
        expect(body.collaborators).toBeDefined();
        const names = body.collaborators.map((c: {name: string}) => c.name);
        expect(names).toContain(user.username);
      });
    });

    // ========================================================================
    // Teams
    // ========================================================================

    test.describe('Teams', () => {
      test('create team, add repo permission, add member', async ({
        superuserApi,
        adminClient,
      }) => {
        const org = await superuserApi.organization();
        const repo = await superuserApi.repository(org.name);
        const team = await superuserApi.team(org.name);
        const user = await superuserApi.user();

        // Add repository write permission to team
        const addTeamPerm = await adminClient.put(
          `/api/v1/repository/${org.name}/${repo.name}/permissions/team/${team.name}`,
          {role: 'write'},
        );
        expect(addTeamPerm.status()).toBe(200);
        const teamPermBody = await addTeamPerm.json();
        expect(teamPermBody.name).toContain(team.name);

        // Add team member
        const addMember = await adminClient.put(
          `/api/v1/organization/${org.name}/team/${team.name}/members/${user.username}`,
        );
        expect(addMember.status()).toBe(200);
        const memberBody = await addMember.json();
        expect(memberBody.name).toContain(user.username);
      });
    });

    // ========================================================================
    // Notifications CRUD
    // ========================================================================

    test.describe('Notifications', () => {
      test('list notifications on empty repo returns 200', async ({
        superuserApi,
        adminClient,
      }) => {
        const org = await superuserApi.organization();
        const repo = await superuserApi.repository(org.name);

        const list = await adminClient.get(
          `/api/v1/repository/${org.name}/${repo.name}/notification/`,
        );
        expect(list.status()).toBe(200);
      });

      test('create, test, reset, get by uuid, and delete notification', async ({
        superuserApi,
        adminClient,
      }) => {
        const org = await superuserApi.organization();
        const repo = await superuserApi.repository(org.name);

        // Create a repo_push notification targeting the owners team
        const create = await adminClient.post(
          `/api/v1/repository/${org.name}/${repo.name}/notification/`,
          {
            event: 'repo_push',
            method: 'quay_notification',
            config: {
              target: {
                name: 'owners',
                kind: 'team',
                is_robot: false,
                avatar: {
                  name: 'owners',
                  hash: 'b132392a317588e56460e77a8fd74229',
                  color: '#1f77b4',
                  kind: 'team',
                },
                is_org_member: true,
              },
            },
            eventConfig: {},
            title: 'new image pushed',
          },
        );
        expect(create.status()).toBe(201);
        const createBody = await create.json();
        const notificationUuid = createBody.uuid;
        expect(notificationUuid).toBeDefined();

        // Test the notification
        const testNotif = await adminClient.post(
          `/api/v1/repository/${org.name}/${repo.name}/notification/${notificationUuid}/test`,
        );
        expect(testNotif.status()).toBe(200);

        // Reset notification failure count
        const reset = await adminClient.post(
          `/api/v1/repository/${org.name}/${repo.name}/notification/${notificationUuid}`,
        );
        expect(reset.status()).toBe(204);

        // Get notification by UUID
        const getByUuid = await adminClient.get(
          `/api/v1/repository/${org.name}/${repo.name}/notification/${notificationUuid}`,
        );
        expect(getByUuid.status()).toBe(200);
        const getBody = await getByUuid.json();
        expect(getBody.uuid).toBe(notificationUuid);

        // Delete notification
        const del = await adminClient.delete(
          `/api/v1/repository/${org.name}/${repo.name}/notification/${notificationUuid}`,
        );
        expect(del.status()).toBe(204);
      });
    });

    // ========================================================================
    // Robot Accounts CRUD
    // ========================================================================

    test.describe('Robot Accounts', () => {
      test('create, get, and list robot accounts under org', async ({
        superuserApi,
        adminClient,
      }) => {
        const org = await superuserApi.organization();
        const robot = await superuserApi.robot(org.name);

        // Get specific robot
        const getBot = await adminClient.get(
          `/api/v1/organization/${org.name}/robots/${robot.shortname}`,
        );
        expect(getBot.status()).toBe(200);

        // List all robots in the org
        const listBots = await adminClient.get(
          `/api/v1/organization/${org.name}/robots?permissions=true&token=false`,
        );
        expect(listBots.status()).toBe(200);
        const listBody = await listBots.json();
        expect(listBody.robots.length).toBeGreaterThanOrEqual(1);
      });

      test('admin can regenerate an org robot token', async ({
        superuserApi,
        adminClient,
      }) => {
        const org = await superuserApi.organization('robotregen');
        const robot = await superuserApi.robot(org.name, 'regenbot');

        const regenResp = await adminClient.post(
          `/api/v1/organization/${org.name}/robots/${robot.shortname}/regenerate`,
        );
        expect(regenResp.status()).toBe(200);
        const regen = await regenResp.json();
        expect(regen.token).toBeTruthy();
      });
    });

    // ========================================================================
    // Robot Federation CRUD
    // ========================================================================

    test.describe('Robot Federation', () => {
      test('create with invalid issuer URL returns 400', async ({
        superuserApi,
        adminClient,
      }) => {
        const org = await superuserApi.organization();
        const robot = await superuserApi.robot(org.name);

        const resp = await adminClient.post(
          `/api/v1/organization/${org.name}/robots/${robot.shortname}/federation`,
          [
            {
              issuer: 'sts.windows.net/250926f3-c788-4a52-acfa-e3aac5386ac1',
              subject: '93VEQl60c7JtJIV9r3gS0FCPTkcpwCDtfEUtD-lgdP4',
              isExpanded: true,
            },
          ],
        );
        expect(resp.status()).toBe(400);
        const body = await resp.json();
        expect(body.error_message).toContain('Issuer must be a URL');
      });

      test('create, get, and delete federation with valid issuer URL', async ({
        superuserApi,
        adminClient,
      }) => {
        const org = await superuserApi.organization();
        const robot = await superuserApi.robot(org.name);

        // Create federation with valid URL
        const create = await adminClient.post(
          `/api/v1/organization/${org.name}/robots/${robot.shortname}/federation`,
          [
            {
              issuer:
                'https://sts.windows.net/250926f3-c788-4a52-acfa-e3aac5386ac1/',
              subject: '93VEQl60c7JtJIV9r3gS0FCPTkcpwCDtfEUtD-lgdP4',
              isExpanded: true,
            },
          ],
        );
        expect(create.status()).toBe(200);

        // Get federation
        const getFed = await adminClient.get(
          `/api/v1/organization/${org.name}/robots/${robot.shortname}/federation`,
        );
        expect(getFed.status()).toBe(200);
        const fedBody = await getFed.json();
        expect(Array.isArray(fedBody)).toBe(true);
        expect(fedBody.length).toBeGreaterThan(0);
        expect(fedBody[0].issuer).toContain(
          'sts.windows.net/250926f3-c788-4a52-acfa-e3aac5386ac1',
        );
        expect(fedBody[0].subject).toContain(
          '93VEQl60c7JtJIV9r3gS0FCPTkcpwCDtfEUtD-lgdP4',
        );

        // Delete federation
        const del = await adminClient.delete(
          `/api/v1/organization/${org.name}/robots/${robot.shortname}/federation`,
        );
        expect(del.status()).toBe(204);
      });
    });

    // ========================================================================
    // Default Permissions / Prototypes
    // ========================================================================

    test.describe('Default Permissions (Prototypes)', () => {
      test('create, list, update, and delete default permission for robot account', async ({
        superuserApi,
        adminClient,
      }) => {
        const org = await superuserApi.organization();
        const robot = await superuserApi.robot(org.name);

        // Create
        const resp = await adminClient.post(
          `/api/v1/organization/${org.name}/prototypes`,
          {
            delegate: {
              name: robot.fullName,
              kind: 'user',
              is_robot: true,
              is_org_member: true,
            },
            role: 'read',
          },
        );
        expect(resp.status()).toBe(200);
        const body = await resp.json();
        expect(body.delegate.name).toBe(robot.fullName);
        const prototypeId = body.id;

        // List
        const list = await adminClient.get(
          `/api/v1/organization/${org.name}/prototypes`,
        );
        expect(list.status()).toBe(200);
        const listBody = await list.json();
        const found = listBody.prototypes.find(
          (p: {id: string}) => p.id === prototypeId,
        );
        expect(found).toBeTruthy();

        // Update role from read to write
        const update = await adminClient.put(
          `/api/v1/organization/${org.name}/prototypes/${prototypeId}`,
          {role: 'write'},
        );
        expect(update.status()).toBe(200);
        const updateBody = await update.json();
        expect(updateBody.role).toBe('write');

        // Delete
        const del = await adminClient.delete(
          `/api/v1/organization/${org.name}/prototypes/${prototypeId}`,
        );
        expect(del.status()).toBe(204);
      });
    });

    // ========================================================================
    // Repository State Changes
    // ========================================================================

    test.describe(
      'Repository State Changes',
      {tag: ['@feature:REPO_MIRROR']},
      () => {
        test('transition repo through MIRROR, READ_ONLY, and NORMAL states', async ({
          superuserApi,
          adminClient,
        }) => {
          const org = await superuserApi.organization();
          const repo = await superuserApi.repository(org.name);

          // Change to MIRROR
          const toMirror = await adminClient.put(
            `/api/v1/repository/${org.name}/${repo.name}/changestate`,
            {state: 'MIRROR'},
          );
          expect(toMirror.status()).toBe(200);
          const mirrorBody = await toMirror.json();
          expect(mirrorBody.success).toBe(true);

          // Change to READ_ONLY
          const toReadOnly = await adminClient.put(
            `/api/v1/repository/${org.name}/${repo.name}/changestate`,
            {state: 'READ_ONLY'},
          );
          expect(toReadOnly.status()).toBe(200);
          const readOnlyBody = await toReadOnly.json();
          expect(readOnlyBody.success).toBe(true);

          // Change back to NORMAL
          const toNormal = await adminClient.put(
            `/api/v1/repository/${org.name}/${repo.name}/changestate`,
            {state: 'NORMAL'},
          );
          expect(toNormal.status()).toBe(200);
          const normalBody = await toNormal.json();
          expect(normalBody.success).toBe(true);
        });
      },
    );
  },
);

// ============================================================================
// Team Email Invitations
// ============================================================================

test.describe(
  'Team Email Invitations',
  {tag: ['@api', '@auth:Database', '@feature:MAILING']},
  () => {
    test('admin can invite user to team by email and revoke the invitation', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('teaminvite');
      const team = await superuserApi.team(org.name, 'inviteteam');
      const email = `${uniqueName('invite')}@example.com`;

      const inviteResp = await adminClient.put(
        `/api/v1/organization/${org.name}/team/${team.name}/invite/${email}`,
      );
      if (inviteResp.status() === 400) {
        test.skip(true, 'Email team invitations not enabled');
        return;
      }
      expect(inviteResp.status()).toBe(200);

      const revokeResp = await adminClient.delete(
        `/api/v1/organization/${org.name}/team/${team.name}/invite/${email}`,
      );
      expect([204, 404]).toContain(revokeResp.status());
    });
  },
);
