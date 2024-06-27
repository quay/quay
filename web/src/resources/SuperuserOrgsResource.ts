import {AxiosResponse} from 'axios';
import {ResourceError, assertHttpCode, throwIfError} from './ErrorHandling';
import axios from 'src/libs/axios';
import {ISuperuserOrgs} from 'src/hooks/UseSuperuserOrgs';

export async function fetchSuperuserOrgs() {
  const superuserOrgsUrl = `/api/v1/superuser/organizations/`;
  const response: AxiosResponse = await axios.get(superuserOrgsUrl);
  assertHttpCode(response.status, 200);
  return response.data?.organizations;
}

export async function deleteOrg(orgName: string) {
  try {
    await axios.delete(`/api/v1/superuser/organizations/${orgName}`);
  } catch (error) {
    throw new ResourceError('Unable to delete organization', orgName, error);
  }
}

export async function bulkDeleteOrgs(organizations: ISuperuserOrgs[]) {
  const responses = await Promise.allSettled(
    organizations.map((org) => deleteOrg(org.name)),
  );
  throwIfError(responses, 'Error deleting organizations');
}
