import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';
import {AxiosResponse} from 'axios';

export async function enableTeamSyncForOrg(
  orgName: string,
  teamName: string,
  groupName: string,
  service: string,
) {
  const enableSyncUrl = `/api/v1/organization/${orgName}/team/${teamName}/syncing`;
  let data = {};
  if (service == 'oidc') {
    data = {
      group_config: `${orgName}:${groupName}`,
    };
  }
  const response: AxiosResponse = await axios.post(enableSyncUrl, data);
  assertHttpCode(response.status, 200);
  return response.data;
}
