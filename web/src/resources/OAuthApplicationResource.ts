import type {
  AssignOAuthApplicationTokenParams,
  CreateOAuthApplicationParams,
  CreateOAuthApplicationTokenParams,
  IOAuthApplication,
  IOAuthApplicationToken,
  OAuthApplicationTokensResponse,
} from './OAuthApplicationTypes';
import axios from 'src/libs/axios';
import {assertHttpCode, ResourceError, throwIfError} from './ErrorHandling';

export async function fetchOAuthApplications(org: string) {
  const response = await axios.get(`/api/v1/organization/${org}/applications`);
  assertHttpCode(response.status, 200);
  return response.data.applications;
}

function oauthApplicationTokensUrl(
  org: string,
  clientId: string,
  tokenUuid?: string,
): string {
  const baseUrl = `/api/v1/organization/${org}/applications/${clientId}/tokens`;
  return tokenUuid ? `${baseUrl}/${tokenUuid}` : baseUrl;
}

export async function fetchOAuthApplicationTokens(
  org: string,
  clientId: string,
  nextPageToken?: string,
): Promise<IOAuthApplicationToken[]> {
  const url = nextPageToken
    ? `${oauthApplicationTokensUrl(
        org,
        clientId,
      )}?next_page=${encodeURIComponent(nextPageToken)}`
    : oauthApplicationTokensUrl(org, clientId);

  try {
    const response = await axios.get(url);
    assertHttpCode(response.status, 200);

    const data = response.data as OAuthApplicationTokensResponse;
    const tokens = data.tokens || [];

    if (data.next_page) {
      const nextTokens = await fetchOAuthApplicationTokens(
        org,
        clientId,
        data.next_page,
      );
      return tokens.concat(nextTokens);
    }

    return tokens;
  } catch (err) {
    if (err instanceof ResourceError) {
      throw err;
    }
    throw new ResourceError(
      'Failed to fetch OAuth application tokens',
      clientId,
      err,
    );
  }
}

export async function createOAuthApplicationToken(
  org: string,
  clientId: string,
  params: CreateOAuthApplicationTokenParams,
): Promise<IOAuthApplicationToken> {
  try {
    const response = await axios.post(
      oauthApplicationTokensUrl(org, clientId),
      params,
    );
    assertHttpCode(response.status, 200);
    return response.data;
  } catch (err) {
    throw new ResourceError(
      'Failed to create OAuth application token',
      clientId,
      err,
    );
  }
}

export async function assignOAuthApplicationTokenToUser(
  clientId: string,
  params: AssignOAuthApplicationTokenParams,
): Promise<{message: string}> {
  const queryParams = new URLSearchParams({
    username: params.username,
    response_type: 'token',
    client_id: clientId,
    scope: params.scope,
    redirect_uri: params.redirect_uri,
    format: 'json',
  });

  try {
    const response = await axios.post(
      `/oauth/authorize/assignuser?${queryParams.toString()}`,
    );
    assertHttpCode(response.status, 200);
    return response.data;
  } catch (err) {
    throw new ResourceError(
      'Failed to assign OAuth application token',
      clientId,
      err,
    );
  }
}

export async function revokeOAuthApplicationToken(
  org: string,
  clientId: string,
  tokenUuid: string,
): Promise<void> {
  try {
    const response = await axios.delete(
      oauthApplicationTokensUrl(org, clientId, tokenUuid),
    );
    assertHttpCode(response.status, 204);
  } catch (err) {
    throw new ResourceError(
      'Failed to revoke OAuth application token',
      tokenUuid,
      err,
    );
  }
}

export async function updateOAuthApplication(
  org: string,
  clientId: string,
  applicationData: Partial<IOAuthApplication>,
) {
  try {
    await axios.put(
      `/api/v1/organization/${org}/applications/${clientId}`,
      applicationData,
    );
  } catch (err) {
    throw new ResourceError(
      'Failed to update OAuth application',
      clientId,
      err,
    );
  }
}

export async function deleteOAuthApplication(
  org: string,
  oauthApp: IOAuthApplication,
) {
  try {
    await axios.delete(
      `/api/v1/organization/${org}/applications/${oauthApp.client_id}`,
    );
  } catch (err) {
    throw new ResourceError(
      'Unable to delete OAuth application:',
      oauthApp.name,
      err,
    );
  }
}

export async function createOAuthApplication(
  orgName: string,
  params: CreateOAuthApplicationParams,
) {
  try {
    await axios.post(`/api/v1/organization/${orgName}/applications`, params);
  } catch (err) {
    throw new ResourceError(
      'Failed to create OAuth application:',
      params.name,
      err,
    );
  }
}

export async function bulkDeleteOAuthApplications(
  orgName: string,
  oauthApplications: IOAuthApplication[],
) {
  const responses = await Promise.allSettled(
    oauthApplications.map((application) =>
      deleteOAuthApplication(orgName, application),
    ),
  );
  throwIfError(responses, 'Unable to delete OAuth applications');
}

export async function resetOAuthApplicationClientSecret(
  org: string,
  clientId: string,
): Promise<IOAuthApplication> {
  try {
    const response = await axios.post(
      `/api/v1/organization/${org}/applications/${clientId}/resetclientsecret`,
    );
    return response.data;
  } catch (err) {
    throw new ResourceError(
      'Failed to reset OAuth application client secret',
      clientId,
      err,
    );
  }
}
