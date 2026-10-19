import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

interface RobotAPIToken {
  uuid: string;
  name: string;
  scope: string;
  token?: string;
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
  },
);
