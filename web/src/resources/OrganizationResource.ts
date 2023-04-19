import {AxiosError, AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {assertHttpCode, BulkOperationError} from './ErrorHandling';

export interface IAvatar {
  name: string;
  hash: string;
  color: string;
  kind: string;
}

export interface IOrganization {
  name: string;
  avatar?: IAvatar;
  can_create_repo?: boolean;
  public?: boolean;
  is_org_admin?: boolean;
  is_admin?: boolean;
  preferred_namespace?: boolean;
  teams?: string[];
}

export async function fetchOrg(orgname: string, signal: AbortSignal) {
  const getOrgUrl = `/api/v1/organization/${orgname}`;
  // TODO: Add return type
  const response: AxiosResponse = await axios.get(getOrgUrl, {signal});
  assertHttpCode(response.status, 200);
  return response.data as IOrganization;
}

export interface SuperUserOrganizations {
  organizations: IOrganization[];
}

export async function fetchOrgsAsSuperUser() {
  const superUserOrgsUrl = `/api/v1/superuser/organizations/`;
  const response: AxiosResponse<SuperUserOrganizations> = await axios.get(
    superUserOrgsUrl,
  );
  assertHttpCode(response.status, 200);
  return response.data?.organizations;
}

export class OrgDeleteError extends Error {
  error: AxiosError;
  org: string;
  constructor(message: string, org: string, error: AxiosError) {
    super(message);
    this.org = org;
    this.error = error;
    Object.setPrototypeOf(this, OrgDeleteError.prototype);
  }
}

export async function deleteOrg(orgname: string, isSuperUser = false) {
  try {
    const deleteApiUrl = isSuperUser
      ? `/api/v1/superuser/organizations/${orgname}`
      : `/api/v1/organization/${orgname}`;
    // TODO: Add return type
    const response: AxiosResponse = await axios.delete(deleteApiUrl);
    assertHttpCode(response.status, 204);
    return response.data;
  } catch (err) {
    throw new OrgDeleteError('failed to delete org ', orgname, err);
  }
}

export async function bulkDeleteOrganizations(
  orgs: string[],
  isSuperUser = false,
) {
  const responses = await Promise.allSettled(
    orgs.map((org) => deleteOrg(org, isSuperUser)),
  );

  // Aggregate failed responses
  const errResponses = responses.filter(
    (r) => r.status == 'rejected',
  ) as PromiseRejectedResult[];

  // If errors, collect and throw
  if (errResponses.length > 0) {
    const bulkDeleteError = new BulkOperationError<OrgDeleteError>(
      'error deleting orgs',
    );
    for (const response of errResponses) {
      const reason = response.reason as OrgDeleteError;
      bulkDeleteError.addError(reason.org, reason);
    }
    throw bulkDeleteError;
  }

  return responses;
}

interface CreateOrgRequest {
  name: string;
  email?: string;
}

export async function createOrg(name: string, email?: string) {
  const createOrgUrl = `/api/v1/organization/`;
  const reqBody: CreateOrgRequest = {name: name};
  if (email) {
    reqBody.email = email;
  }
  const response = await axios.post(createOrgUrl, reqBody);
  assertHttpCode(response.status, 201);
  return response.data;
}
