import {AxiosError, AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {ResourceError, assertHttpCode, throwIfError} from './ErrorHandling';
import {ITeamRepoPerms, ITeams} from 'src/hooks/UseTeams';

export class TeamDeleteError extends Error {
  error: Error;
  team: string;
  constructor(message: string, team: string, error: AxiosError) {
    super(message);
    this.team = team;
    this.error = error;
    Object.setPrototypeOf(this, TeamDeleteError.prototype);
  }
}

export async function createNewTeamForNamespace(
  namespace: string,
  teamName: string,
  description?: string,
) {
  const createTeamUrl = `/api/v1/organization/${namespace}/team/${teamName}`;
  const payload = {name: teamName, role: 'member'};
  if (description) {
    payload['description'] = description;
  }
  const response: AxiosResponse = await axios.put(createTeamUrl, payload);
  assertHttpCode(response.status, 200);
  return response.data;
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

export async function updateTeamDetailsForNamespace(
  namespace: string,
  teamName: string,
  teamRole: string,
  description?: string,
) {
  const updateTeamUrl = `/api/v1/organization/${namespace}/team/${teamName}`;
  const payload = {name: teamName, role: teamRole};
  if (description !== undefined) {
    payload['description'] = description;
  }
  const response: AxiosResponse = await axios.put(updateTeamUrl, payload);
  assertHttpCode(response.status, 200);
  return response.data?.name;
}

export async function updateTeamRepoPerm(
  orgName: string,
  teamName: string,
  teamRepoPerms: ITeamRepoPerms[],
) {
  const responses = await Promise.allSettled(
    teamRepoPerms?.map(async (repoPerm) => {
      if (repoPerm.role === 'none') {
        try {
          const response: AxiosResponse = await axios.delete(
            `/api/v1/repository/${orgName}/${repoPerm.repoName}/permissions/team/${teamName}`,
          );
          assertHttpCode(response.status, 204);
        } catch (error) {
          if (error.response.status !== 400) {
            throw new ResourceError(
              'Unable to update repository permission for repo',
              repoPerm.repoName,
              error,
            );
          }
        }
      } else {
        const updateTeamUrl = `/api/v1/repository/${orgName}/${repoPerm.repoName}/permissions/team/${teamName}`;
        const payload = {role: repoPerm.role};
        try {
          const response: AxiosResponse = await axios.put(
            updateTeamUrl,
            payload,
          );
          assertHttpCode(response.status, 200);
        } catch (error) {
          throw new ResourceError(
            'Unable to update repository permission for repo',
            repoPerm.repoName,
            error,
          );
        }
      }
    }),
  );
  throwIfError(responses, 'Error updating team repo permissions');
}

export async function fetchTeamsForNamespace(
  org: string,
  signal?: AbortSignal,
) {
  const teamsForOrgUrl = `/api/v1/organization/${org}`;
  const teamsResponse = await axios.get(teamsForOrgUrl, {signal});
  assertHttpCode(teamsResponse.status, 200);
  return teamsResponse.data?.teams;
}

export async function fetchTeamRepoPermsForOrg(
  org: string,
  teamName: string,
  signal?: AbortSignal,
) {
  const response: AxiosResponse = await axios.get(
    `/api/v1/organization/${org}/team/${teamName}/permissions`,
    {signal},
  );
  return response.data.permissions;
}

export async function deleteTeamForOrg(orgName: string, teamName: string) {
  try {
    await axios.delete(`/api/v1/organization/${orgName}/team/${teamName}`);
  } catch (error) {
    throw new ResourceError('Unable to delete team', teamName, error);
  }
}

export async function bulkDeleteTeams(orgName: string, teams: ITeams[]) {
  const responses = await Promise.allSettled(
    teams.map((team) => deleteTeamForOrg(orgName, team.name)),
  );
  throwIfError(responses, 'Error deleting teams');
}
