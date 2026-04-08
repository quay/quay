import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';
import {AxiosResponse} from 'axios';

export type SupportedService = 'ldap' | 'keystone' | 'oidc';

export async function enableTeamSyncForOrg(
  orgName: string,
  teamName: string,
  groupName: string,
  service: SupportedService,
) {
  const enableSyncUrl = `/api/v1/organization/${orgName}/team/${teamName}/syncing`;
  let data = {};
  if (service === 'oidc') {
    data = {
      group_name: groupName,
    };
  } else if (service === 'ldap') {
    data = {
      group_dn: groupName,
    };
  } else if (service === 'keystone') {
    data = {
      group_id: groupName,
    };
  } else {
    throw new Error(`Unsupported team sync service: ${service}`);
  }
  const response: AxiosResponse = await axios.post(enableSyncUrl, data);
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function removeTeamSyncForOrg(orgName: string, teamName: string) {
  const enableSyncUrl = `/api/v1/organization/${orgName}/team/${teamName}/syncing`;
  const response: AxiosResponse = await axios.delete(enableSyncUrl);
  assertHttpCode(response.status, 200);
  return response.data;
}
