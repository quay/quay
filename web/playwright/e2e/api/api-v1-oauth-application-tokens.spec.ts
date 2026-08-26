import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

interface OAuthApplicationToken {
  uuid: string;
  name: string | null;
  scope: string;
  token?: string;
  expires_at: string | null;
  created: string | null;
  created_by: string | null;
  last_accessed: string | null;
}

interface OAuthApplicationTokensResponse {
  tokens: OAuthApplicationToken[];
}

test.describe(
  'OAuth Application Tokens',
  {tag: ['@api', '@organization', '@auth:Database']},
  () => {
    test('organization admin creates, lists, and revokes application tokens', async ({
      authenticatedRequest,
      request,
      api,
    }) => {
      const org = await api.organization('oauthtokens');
      const app = await api.oauthApplication(org.name, 'tokenapp');
      const csrfToken = await api.raw.getToken();

      const createResponse = await authenticatedRequest.post(
        `${API_URL}/api/v1/organization/${org.name}/applications/${app.clientId}/tokens`,
        {
          headers: {'X-CSRF-Token': csrfToken},
          data: {
            name: 'Playwright lifecycle token',
            scope: 'repo:read,user:read',
            expiration: 3600,
          },
        },
      );

      expect(createResponse.status()).toBe(200);
      const created = (await createResponse.json()) as OAuthApplicationToken;
      expect(created.uuid).toBeTruthy();
      expect(created.token).toBeTruthy();
      expect(created.name).toBe('Playwright lifecycle token');
      expect(created.scope).toBe('repo:read user:read');
      expect(created.created_by).toBeTruthy();
      expect(created.expires_at).toBeTruthy();
      expect(created.created).toBeTruthy();
      expect(created.last_accessed).toBeNull();

      const listResponse = await authenticatedRequest.get(
        `${API_URL}/api/v1/organization/${org.name}/applications/${app.clientId}/tokens`,
      );

      expect(listResponse.status()).toBe(200);
      const listed =
        (await listResponse.json()) as OAuthApplicationTokensResponse;
      const listedToken = listed.tokens.find(
        (token) => token.uuid === created.uuid,
      );
      expect(listedToken).toBeDefined();
      expect(listedToken?.name).toBe('Playwright lifecycle token');
      expect(listedToken?.scope).toBe('repo:read user:read');
      expect(listedToken?.token).toBeUndefined();

      const authorizedResponse = await request.get(`${API_URL}/api/v1/user/`, {
        headers: {Authorization: `Bearer ${created.token}`},
      });
      expect(authorizedResponse.status()).toBe(200);

      const deleteResponse = await authenticatedRequest.delete(
        `${API_URL}/api/v1/organization/${org.name}/applications/${app.clientId}/tokens/${created.uuid}`,
        {headers: {'X-CSRF-Token': csrfToken}},
      );

      expect(deleteResponse.status()).toBe(204);

      const deletedListResponse = await authenticatedRequest.get(
        `${API_URL}/api/v1/organization/${org.name}/applications/${app.clientId}/tokens`,
      );
      expect(deletedListResponse.status()).toBe(200);
      const afterDelete =
        (await deletedListResponse.json()) as OAuthApplicationTokensResponse;
      expect(
        afterDelete.tokens.find((token) => token.uuid === created.uuid),
      ).toBeUndefined();

      const revokedResponse = await request.get(`${API_URL}/api/v1/user/`, {
        headers: {Authorization: `Bearer ${created.token}`},
      });
      expect(revokedResponse.status()).toBe(401);
    });
  },
);
