import {test, expect, uniqueName} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {RawApiClient} from '../../utils/api';
import {API_URL} from '../../utils/config';

const REGISTERED_REDIRECT = 'https://client.example.com/oauth/callback';
const UNREGISTERED_REDIRECT = 'https://evil.example/oauth/callback';

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

test.describe(
  'OAuth authorization boundaries',
  {tag: ['@api', '@auth:Database', '@superuser']},
  () => {
    test('authorize keeps tokens on the registered redirect and to org admins; only the owner revokes', async ({
      api,
      authenticatedRequest,
      freshUser,
      request,
      browser,
      traceparent,
    }) => {
      const org = await api.organization('oauthauthz');
      const appName = uniqueName('authz');
      // Deleted with the org.
      const app = await api.raw.createOAuthApplication(
        org.name,
        appName,
        REGISTERED_REDIRECT,
      );
      const csrfToken = await api.raw.getToken();

      const authorizePath = (redirectUri: string) =>
        `/oauth/authorize?${new URLSearchParams({
          format: 'json',
          response_type: 'token',
          client_id: app.client_id,
          scope: 'user:read',
          redirect_uri: redirectUri,
        })}`;

      const consent = await authenticatedRequest.get(
        `${API_URL}${authorizePath(REGISTERED_REDIRECT)}`,
        {maxRedirects: 0},
      );
      expect(consent.status()).toBe(200);
      const consentBody = await consent.json();
      expect(consentBody.scopes.map((s: {scope: string}) => s.scope)).toEqual([
        'user:read',
      ]);
      expect(consentBody.csrf_token_val).toBeTruthy();

      const mismatch = await authenticatedRequest.get(
        `${API_URL}${authorizePath(UNREGISTERED_REDIRECT)}`,
        {maxRedirects: 0},
      );
      expect(mismatch.status()).toBe(302);
      const mismatchLocation = new URL(mismatch.headers()['location']);
      expect(`${mismatchLocation.origin}${mismatchLocation.pathname}`).toBe(
        REGISTERED_REDIRECT,
      );
      expect(mismatchLocation.searchParams.get('error')).toBe(
        'redirect_uri_mismatch',
      );

      const grant = await authenticatedRequest.post(
        `${API_URL}/oauth/authorizeapp`,
        {
          form: {
            client_id: app.client_id,
            redirect_uri: REGISTERED_REDIRECT,
            scope: 'user:read',
            response_type: 'token',
            _csrf_token: consentBody.csrf_token_val,
          },
          maxRedirects: 0,
        },
      );
      expect(grant.status()).toBe(302);
      const grantLocation = new URL(grant.headers()['location']);
      expect(`${grantLocation.origin}${grantLocation.pathname}`).toBe(
        REGISTERED_REDIRECT,
      );
      const accessToken = new URLSearchParams(grantLocation.hash.slice(1)).get(
        'access_token',
      );
      expect(accessToken).toBeTruthy();
      const asBearer = () =>
        request.get(`${API_URL}/api/v1/user/`, {
          headers: {Authorization: `Bearer ${accessToken}`},
        });
      const owner = await asBearer();
      expect(owner.status()).toBe(200);
      expect((await owner.json()).username).toBe(TEST_USERS.user.username);

      // With the scope already granted, authorize issues a token without a
      // consent step, so this is the path that must refuse the redirect.
      const leak = await authenticatedRequest.get(
        `${API_URL}${authorizePath(UNREGISTERED_REDIRECT)}`,
        {maxRedirects: 0},
      );
      expect(leak.headers()['location'] ?? '').not.toContain('access_token');
      expect(leak.status()).toBe(400);
      expect(await leak.json()).toEqual({error: 'invalid_request'});

      const authorizations = await authenticatedRequest.get(
        `${API_URL}/api/v1/user/authorizations`,
      );
      expect(authorizations.status()).toBe(200);
      const granted = (
        (await authorizations.json()).authorizations as Array<{
          uuid: string;
          application: {name: string};
        }>
      ).filter((a) => a.application.name === appName);
      expect(granted).toHaveLength(1);
      const authorizationPath = `/api/v1/user/authorizations/${granted[0].uuid}`;

      const outsiderContext = await browser.newContext({
        extraHTTPHeaders: {traceparent: traceparent.traceparent},
      });
      try {
        const outsider = new RawApiClient(outsiderContext.request, API_URL);
        await outsider.signIn(freshUser.user.username, freshUser.user.password);
        expect(
          (await outsider.get(authorizePath(REGISTERED_REDIRECT))).status(),
        ).toBe(403);
        expect((await outsider.delete(authorizationPath)).status()).toBe(404);
      } finally {
        await outsiderContext.close();
      }
      expect((await asBearer()).status()).toBe(200);

      const revoke = await authenticatedRequest.delete(
        `${API_URL}${authorizationPath}`,
        {headers: {'X-CSRF-Token': csrfToken}},
      );
      expect(revoke.status()).toBe(204);
      expect((await asBearer()).status()).toBe(401);
    });

    test('org admin cannot mint an application token with super:user or an unknown scope', async ({
      api,
      authenticatedRequest,
    }) => {
      const org = await api.organization('oauthmint');
      // Deleted with the org.
      const app = await api.raw.createOAuthApplication(
        org.name,
        uniqueName('mint'),
      );
      const csrfToken = await api.raw.getToken();

      const mint = (scope: string) =>
        authenticatedRequest.post(
          `${API_URL}/api/v1/organization/${org.name}/applications/${app.client_id}/tokens`,
          {
            headers: {'X-CSRF-Token': csrfToken},
            data: {name: 'boundary', scope},
          },
        );
      expect((await mint('super:user')).status()).toBe(403);
      expect((await mint('bogus:scope')).status()).toBe(400);
    });
  },
);
