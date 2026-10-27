import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

interface RobotAPIToken {
  uuid: string;
  name: string;
  scope: string;
  token?: string;
  last_accessed?: string | null;
}

interface RobotAPITokensResponse {
  tokens: RobotAPIToken[];
}

test.describe(
  'Robot API Tokens',
  {
    tag: [
      '@api',
      '@organization',
      '@auth:Database',
      '@feature:ROBOT_API_TOKENS',
    ],
  },
  () => {
    test(
      'organization admin creates, authenticates with, lists, and revokes a robot API token',
      {tag: '@PROJQUAY-11090'},
      async ({authenticatedRequest, api, request}) => {
        const org = await api.organization('robotapitokens');
        const robot = await api.robot(org.name, 'tokenbot');
        const repository = await api.repository(org.name, 'robotapitoken');
        await api.repositoryPermission(
          org.name,
          repository.name,
          'user',
          robot.fullName,
          'read',
        );
        const csrfToken = await api.raw.getToken();
        const tokensUrl = `${API_URL}/api/v1/organization/${org.name}/robots/${robot.shortname}/tokens`;

        const createResponse = await authenticatedRequest.post(tokensUrl, {
          headers: {'X-CSRF-Token': csrfToken},
          data: {
            name: 'Playwright robot API token',
            scope: 'repo:read',
            expiration: 3600,
          },
        });

        expect(createResponse.status()).toBe(200);
        const created = (await createResponse.json()) as RobotAPIToken;
        expect(created.uuid).toBeTruthy();
        expect(created.token).toMatch(/^qro_[A-Za-z0-9]{60}$/);
        expect(created.name).toBe('Playwright robot API token');
        expect(created.scope).toBe('repo:read');

        // Use the opaque credential through a repository read path, which is
        // supported by the token's repo:read scope and the robot's permission.
        // `request` is an isolated context, so no session cookie can satisfy
        // this request.
        const authenticatedAsRobot = await request.get(
          `${API_URL}/api/v1/repository/${repository.fullName}`,
          {headers: {Authorization: `Bearer ${created.token}`}},
        );
        expect(authenticatedAsRobot.status()).toBe(200);
        await expect(authenticatedAsRobot.json()).resolves.toMatchObject({
          name: repository.name,
          namespace: org.name,
        });

        const listResponse = await authenticatedRequest.get(tokensUrl);
        expect(listResponse.status()).toBe(200);
        const listed = (await listResponse.json()) as RobotAPITokensResponse;
        const listedToken = listed.tokens.find(
          (token) => token.uuid === created.uuid,
        );
        expect(listedToken).toBeDefined();
        expect(listedToken?.token).toBeUndefined();

        const deleteResponse = await authenticatedRequest.delete(
          `${tokensUrl}/${created.uuid}`,
          {headers: {'X-CSRF-Token': csrfToken}},
        );
        expect(deleteResponse.status()).toBe(204);

        const deletedListResponse = await authenticatedRequest.get(tokensUrl);
        expect(deletedListResponse.status()).toBe(200);
        const afterDelete =
          (await deletedListResponse.json()) as RobotAPITokensResponse;
        expect(afterDelete.tokens).not.toContainEqual(
          expect.objectContaining({uuid: created.uuid}),
        );
      },
    );

    test(
      'global readonly superuser lists robot API tokens but cannot create or revoke them',
      {tag: '@PROJQUAY-13786'},
      async ({authenticatedRequest, api, readonlyClient}) => {
        const org = await api.organization('robotapitokensro');
        const robot = await api.robot(org.name, 'tokenbot');
        const csrfToken = await api.raw.getToken();
        const robotPath = `/api/v1/organization/${org.name}/robots/${robot.shortname}`;
        const tokensPath = `${robotPath}/tokens`;
        const tokenRequest = {
          name: 'Readonly superuser visible token',
          scope: 'repo:read',
          expiration: 3600,
        };

        const createResponse = await authenticatedRequest.post(
          `${API_URL}${tokensPath}`,
          {headers: {'X-CSRF-Token': csrfToken}, data: tokenRequest},
        );
        expect(createResponse.status()).toBe(200);
        const created = (await createResponse.json()) as RobotAPIToken;

        const listResponse = await readonlyClient.get(tokensPath);
        expect(listResponse.status()).toBe(200);
        const listed = (await listResponse.json()) as RobotAPITokensResponse;
        const listedToken = listed.tokens.find(
          (token) => token.uuid === created.uuid,
        );
        expect(listedToken).toBeDefined();
        expect(listedToken?.token).toBeUndefined();

        const scopesResponse = await readonlyClient.get(
          `${robotPath}/mintable-scopes`,
        );
        expect(scopesResponse.status()).toBe(200);
        await expect(scopesResponse.json()).resolves.toEqual({scopes: []});

        const readonlyCreate = await readonlyClient.post(
          tokensPath,
          tokenRequest,
        );
        expect(readonlyCreate.status()).toBe(403);

        const readonlyRevoke = await readonlyClient.delete(
          `${tokensPath}/${created.uuid}`,
        );
        expect(readonlyRevoke.status()).toBe(403);

        const afterResponse = await authenticatedRequest.get(
          `${API_URL}${tokensPath}`,
        );
        expect(afterResponse.status()).toBe(200);
        const after = (await afterResponse.json()) as RobotAPITokensResponse;
        expect(after.tokens.map((token) => token.uuid)).toEqual([created.uuid]);
      },
    );

    test(
      'authenticating with a robot API token records the robot last_accessed',
      {tag: '@PROJQUAY-13785'},
      async ({authenticatedRequest, api, request}) => {
        const org = await api.organization('robotlastaccess');
        const robot = await api.robot(org.name, 'accessbot');
        const repository = await api.repository(org.name, 'robotlastaccess');
        await api.repositoryPermission(
          org.name,
          repository.name,
          'user',
          robot.fullName,
          'read',
        );
        const csrfToken = await api.raw.getToken();
        const robotUrl = `${API_URL}/api/v1/organization/${org.name}/robots/${robot.shortname}`;

        // A robot that has never authenticated has no last_accessed.
        const unused = await authenticatedRequest.get(robotUrl);
        expect(unused.status()).toBe(200);
        expect((await unused.json()).last_accessed).toBeNull();

        const createResponse = await authenticatedRequest.post(
          `${robotUrl}/tokens`,
          {
            headers: {'X-CSRF-Token': csrfToken},
            data: {
              name: 'Playwright last_accessed token',
              scope: 'repo:read',
              expiration: 3600,
            },
          },
        );
        expect(createResponse.status()).toBe(200);
        const created = (await createResponse.json()) as RobotAPIToken;

        // Bearer use of the token on the API is a robot authentication.
        const authenticatedAsRobot = await request.get(
          `${API_URL}/api/v1/repository/${repository.fullName}`,
          {headers: {Authorization: `Bearer ${created.token}`}},
        );
        expect(authenticatedAsRobot.status()).toBe(200);

        const used = await authenticatedRequest.get(robotUrl);
        expect(used.status()).toBe(200);
        const usedRobot = await used.json();
        expect(usedRobot.last_accessed).toEqual(expect.any(String));
        expect(Date.parse(usedRobot.last_accessed)).not.toBeNaN();

        // The token's own last_accessed keeps working as before.
        const listResponse = await authenticatedRequest.get(
          `${robotUrl}/tokens`,
        );
        expect(listResponse.status()).toBe(200);
        const listed = (await listResponse.json()) as RobotAPITokensResponse;
        const listedToken = listed.tokens.find(
          (token) => token.uuid === created.uuid,
        );
        expect(listedToken?.last_accessed).toEqual(expect.any(String));
      },
    );
  },
);
