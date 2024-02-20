import {ITeamMembersResponse} from 'src/hooks/UseMembers';
import {IAvatar} from './OrganizationResource';
import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';
import {AxiosResponse} from 'axios';

export interface IMemberTeams {
  name: string;
  avatar: IAvatar;
}
export interface IMembers {
  name: string;
  kind: string;
  teams?: IMemberTeams[];
  repositories: string[];
}

export async function fetchAllMembers(orgnames: string[], signal: AbortSignal) {
  return await Promise.all(
    orgnames.map((org) => fetchMembersForOrg(org, signal)),
  );
}

export async function fetchMembersForOrg(
  orgname: string,
  signal: AbortSignal,
): Promise<IMembers[]> {
  const getMembersUrl = `/api/v1/organization/${orgname}/members`;
  const response = await axios.get(getMembersUrl, {signal});
  assertHttpCode(response.status, 200);
  return response.data?.members;
}

export async function fetchCollaboratorsForOrg(
  orgname: string,
  signal: AbortSignal,
): Promise<IMembers[]> {
  const getCollaboratorsUrl = `/api/v1/organization/${orgname}/collaborators`;
  const response = await axios.get(getCollaboratorsUrl, {signal});
  assertHttpCode(response.status, 200);
  return response.data?.collaborators;
}

export async function fetchTeamMembersForOrg(
  org: string,
  teamName: string,
  signal?: AbortSignal,
): Promise<ITeamMembersResponse> {
  const teamMemberUrl = `/api/v1/organization/${org}/team/${teamName}/members?includePending=true`;
  const teamMembersResponse = await axios.get(teamMemberUrl, {signal});
  assertHttpCode(teamMembersResponse.status, 200);
  return teamMembersResponse?.data;
}

export async function deleteTeamMemberForOrg(
  orgName: string,
  teamName: string,
  memberName: string,
) {
  const response = await axios.delete(
    `/api/v1/organization/${orgName}/team/${teamName}/members/${memberName}`,
  );
  assertHttpCode(response.status, 204);
}

export async function deleteCollaboratorForOrg(
  orgName: string,
  collaborator: string,
) {
  await axios.delete(`/api/v1/organization/${orgName}/members/${collaborator}`);
}

export async function addMemberToTeamForOrg(
  orgName: string,
  teamName: string,
  member: string,
) {
  const addMemberUrl = `/api/v1/organization/${orgName}/team/${teamName}/members/${member}`;
  const response: AxiosResponse = await axios.put(addMemberUrl, {});
  assertHttpCode(response.status, 200);
  return response.data;
}
