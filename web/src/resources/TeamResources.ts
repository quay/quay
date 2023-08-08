import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';

export async function createNewTeamForNamespac(
  namespace: string,
  name: string,
  description: string,
) {
  const createTeamUrl = `/api/v1/organization/${namespace}/team/${name}`;
  const payload = {name: name, role: 'member', description: description};
  const response: AxiosResponse = await axios.put(createTeamUrl, payload);
  assertHttpCode(response.status, 200);
  return response.data?.name;
}

export async function updateTeamForRobot(
  namespace: string,
  teamName: string,
  robotName: string,
) {
  const robotNameWithOrg = `${namespace}+${robotName}`;
  const createTeamUrl = `/api/v1/organization/${namespace}/team/${teamName}/members/${robotNameWithOrg}`;
  const response: AxiosResponse = await axios.put(createTeamUrl, {});
  assertHttpCode(response.status, 200);
  return response.data?.name;
}
