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
  {tag: ['@api', '@organization', '@auth:Database']},
  () => {
    test(
      'organization admin creates, lists, and revokes a robot API token',
      {tag: '@PROJQUAY-11090'},
      async ({authenticatedRequest, api}) => {
        const org = await api.organization('robotapitokens');
        const robot = await api.robot(org.name, 'tokenbot');
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
