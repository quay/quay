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
  id: string,
  newRole: string,
) {
  try {
    await axios.put(`/api/v1/organization/${org}/applications/${id}`, {
      id: id,
      role: newRole.toLowerCase(),
    });
  } catch (err) {
    throw new ResourceError('failed to set default permissions', newRole, err);
  }
}

export async function deleteOAuthApplication(
  org: string,
  perm: IOAuthApplication,
) {
  try {
    await axios.delete(`/api/v1/organization/${org}/prototypes/${perm.id}`);
  } catch (err) {
    throw new ResourceError(
      'Unable to delete default permission created by:',
      perm.createdBy,
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
      'failed to create oauth application: ',
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
  throwIfError(responses, 'Unable to delete default permissions');
}
