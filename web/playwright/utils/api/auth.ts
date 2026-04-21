/**
 * Authentication helpers for API tests.
 *
 * These functions handle programmatic user initialization, creation, and
 * token acquisition without any browser interaction.
 */

import {APIRequestContext} from '@playwright/test';

import {requestCsrfToken} from './csrf';

/**
 * Initialize the first superuser via the Quay initialize API.
 * Only works when FEATURE_USER_INITIALIZE is enabled and no users exist yet.
 *
 * @returns The access token for the superuser
 */
export async function initializeSuperuser(
  request: APIRequestContext,
  baseUrl: string,
  username: string,
  password: string,
  email: string,
): Promise<string> {
  const response = await request.post(`${baseUrl}/api/v1/user/initialize`, {
    data: {
      username,
      password,
      email,
      access_token: true,
    },
  });

  if (!response.ok()) {
    const body = await response.text();
    // If user already exists or the initialize endpoint is disabled (404),
    // fall back to signing in with the provided credentials.
    if (body.includes('already') || response.status() === 404) {
      return getAccessToken(request, baseUrl, username, password);
    }
    throw new Error(
      `Failed to initialize superuser: ${response.status()} - ${body}`,
    );
  }

  const data = await response.json();
  return data.access_token;
}

/**
 * Get an access token by signing in and fetching the CSRF token.
 * Returns the CSRF token which can be used for subsequent API calls.
 */
export async function getAccessToken(
  request: APIRequestContext,
  baseUrl: string,
  username: string,
  password: string,
): Promise<string> {
  // Fetch initial CSRF token (pre-login session)
  const csrfToken = await requestCsrfToken(request, baseUrl);

  // Sign in — this creates a new session, invalidating the old CSRF token
  const signinResponse = await request.post(`${baseUrl}/api/v1/signin`, {
    headers: {'X-CSRF-Token': csrfToken},
    data: {username, password},
  });
  if (!signinResponse.ok()) {
    const body = await signinResponse.text();
    throw new Error(
      `Failed to sign in as ${username}: ${signinResponse.status()} - ${body}`,
    );
  }

  // Fetch a fresh CSRF token from the authenticated session
  return requestCsrfToken(request, baseUrl);
}

/**
 * Create an OAuth application in an organization and generate an OAuth token.
 * This is the programmatic equivalent of the browser-based OAuth flow.
 *
 * @returns The OAuth access token
 */
export async function createOAuthToken(
  request: APIRequestContext,
  baseUrl: string,
  csrfToken: string,
  orgName: string,
  appName: string,
): Promise<string> {
  // Create an OAuth application
  const appResponse = await request.post(
    `${baseUrl}/api/v1/organization/${orgName}/applications`,
    {
      headers: {'X-CSRF-Token': csrfToken},
      data: {
        name: appName,
        description: 'API test OAuth app',
        redirect_uri: `${baseUrl}/oauth/localapp`,
        application_uri: baseUrl,
      },
    },
  );

  if (!appResponse.ok()) {
    const body = await appResponse.text();
    throw new Error(
      `Failed to create OAuth app: ${appResponse.status()} - ${body}`,
    );
  }

  const appData = await appResponse.json();
  const clientId = appData.client_id;

  // Generate a token by authorizing the app.
  // Disable redirect following so we can read the Location header from the
  // 302 response — the token is in the URL fragment of the redirect target.
  const authorizeResponse = await request.post(`${baseUrl}/oauth/authorize`, {
    headers: {
      'X-CSRF-Token': csrfToken,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    form: {
      client_id: clientId,
      redirect_uri: `${baseUrl}/oauth/localapp`,
      scope: 'repo:admin org:admin super:user user:admin user:read',
      response_type: 'token',
    },
    maxRedirects: 0,
  });

  // The authorize endpoint redirects with the token in the fragment
  const redirectUrl = authorizeResponse.headers()['location'] || '';
  const tokenMatch = redirectUrl.match(/access_token=([^&]+)/);
  if (tokenMatch) {
    return tokenMatch[1];
  }

  // If redirect didn't work, the response body might contain the token
  const body = await authorizeResponse.text();
  const bodyMatch = body.match(/access_token=([^&"]+)/);
  if (bodyMatch) {
    return bodyMatch[1];
  }

  throw new Error(
    `Failed to extract OAuth token from authorize response (status: ${authorizeResponse.status()})`,
  );
}

/**
 * Get a V2 registry bearer token for Docker Registry API operations.
 *
 * @param scope - V2 auth scope, e.g. "repository:org/repo:pull,push"
 * @returns The bearer token
 */
export async function getV2Token(
  request: APIRequestContext,
  baseUrl: string,
  username: string,
  password: string,
  scope?: string,
): Promise<string> {
  const params = new URLSearchParams({
    service: new URL(baseUrl).host,
    ...(scope ? {scope} : {}),
  });

  const response = await request.get(
    `${baseUrl}/v2/auth?${params.toString()}`,
    {
      headers: {
        Authorization: `Basic ${Buffer.from(`${username}:${password}`).toString(
          'base64',
        )}`,
      },
    },
  );

  if (!response.ok()) {
    const body = await response.text();
    throw new Error(`Failed to get V2 token: ${response.status()} - ${body}`);
  }

  const data = await response.json();
  return data.token;
}
