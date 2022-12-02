import {IPrototype} from 'src/hooks/UseDefaultPermissions';
import axios from 'src/libs/axios';
import {assertHttpCode, ResourceError} from './ErrorHandling';
import {RepoMemberPermissions} from './RepositoryResource';

export async function fetchDefaultPermissions(org: string) {
  const response = await axios.get(`/api/v1/organization/${org}/prototypes`);
  assertHttpCode(response.status, 200);
  return response.data.prototypes;
}

export async function updateDefaultPermission(
  org: string,
  id: string,
  newRole: string,
) {
  try {
    await axios.put(`/api/v1/organization/${org}/prototypes/${id}`, {
      id: id,
      role: newRole.toLowerCase(),
    });
  } catch (err) {
    throw new ResourceError('failed to set default permissions', newRole, err);
  }
}

export async function deleteDefaultPermission(org: string, id: string) {
  try {
    await axios.delete(`/api/v1/organization/${org}/prototypes/${id}`);
  } catch (err) {
    console.error('Unable to delete default permission', err);
  }
}

export async function createDefaultPermission(
  orgName: string,
  permObj: IPrototype,
) {
  try {
    await axios.post(`/api/v1/organization/${orgName}/prototypes`, permObj);
  } catch (err) {
    throw new ResourceError(
      'failed to create default permissions for creator:',
      permObj.activating_user.name,
      err,
    );
  }
}

export async function addRepoPermissionToTeam(
  orgName: string,
  repoName: string,
  teamName: string,
  newRole: string,
) {
  try {
    await axios.put(
      `/api/v1/repository/${orgName}/${repoName}/permissions/team/${teamName}`,
      {role: newRole.toLowerCase()},
    );
  } catch (err) {
    console.error('Unable to add repo permissions for team', err);
  }
}
