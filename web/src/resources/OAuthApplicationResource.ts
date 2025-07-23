import {
  CreateOAuthApplicationParams,
  IOAuthApplication,
} from 'src/hooks/UseOAuthApplications';
import axios from 'src/libs/axios';
import {assertHttpCode, ResourceError, throwIfError} from './ErrorHandling';

export async function fetchOAuthApplications(org: string) {
  const response = await axios.get(`/api/v1/organization/${org}/applications`);
  assertHttpCode(response.status, 200);
  return response.data.applications;
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
