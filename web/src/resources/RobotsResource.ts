import {AxiosError, AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {assertHttpCode, BulkOperationError} from './ErrorHandling';

export interface IRobot {
  name: string;
  created: string;
  last_accessed: string;
  teams?: string[];
  repositories?: string[];
  description: string;
}

export interface IRobotRepoPerms {
  name: string;
  permission: string;
  last_modified: string;
}

export interface IRobotTeamAvatar {
  color: string;
  hash: string;
  kind: string;
  name: string;
}

export interface IRobotTeam {
  avatar: IRobotTeamAvatar;
  can_view: boolean;
  is_synced: boolean;
  member_count: number;
  name: string;
  repo_count: 0;
  role: string;
}

export interface IRepoPerm {
  reponame: string;
  permission: string;
}

export interface IRobotToken {
  name: string;
  created: string;
  last_accessed: string;
  description: string;
  token: string;
  unstructured_metadata: object;
}

export interface IRobotFederationConfig {
  issuer: string;
  subject: string;
}

export async function fetchAllRobots(orgnames: string[], signal: AbortSignal) {
  return await Promise.all(
    orgnames.map((org) => fetchRobotsForNamespace(org, false, signal)),
  );
}

export class RobotDeleteError extends Error {
  error: AxiosError;
  robotName: string;
  constructor(message: string, robotName: string, error: AxiosError) {
    super(message);
    this.robotName = robotName;
    this.error = error;
    Object.setPrototypeOf(this, RobotDeleteError.prototype);
  }
}

export async function fetchRobotsForNamespace(
  orgname: string,
  isUser = false,
  signal: AbortSignal,
): Promise<IRobot[]> {
  const userOrOrgPath = isUser ? 'user' : `organization/${orgname}`;
  const getRobotsUrl = `/api/v1/${userOrOrgPath}/robots?permissions=true&token=false`;
  const response: AxiosResponse = await axios.get(getRobotsUrl, {signal});
  assertHttpCode(response.status, 200);
  return response.data?.robots;
}

export async function addDefaultPermsForRobot(
  orgname: string,
  robotname: string,
  permission: string,
  isUser = false,
): Promise<IRobot[]> {
  const robotNameWithOrg = `${orgname}+${robotname}`;
  const updatePermsUrl = `/api/v1/organization/${orgname}/prototypes`;
  const delegate = {
    name: robotNameWithOrg,
    kind: 'user',
    is_robot: true,
  };
  const payload = {delegate: delegate, role: permission.toLowerCase()};
  const response: AxiosResponse = await axios.post(updatePermsUrl, payload);
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function updateRepoPermsForRobot(
  orgname: string,
  robotname: string,
  reponame: string,
  permission: string,
  isUser = false,
): Promise<IRobot[]> {
  const robotNameWithOrg = `${orgname}+${robotname}`;
  const updatePermsUrl = `/api/v1/repository/${orgname}/${reponame}/permissions/user/${robotNameWithOrg}`;
  const payload = {role: permission.toLowerCase()};
  const response: AxiosResponse = await axios.put(updatePermsUrl, payload);
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function bulkUpdateRepoPermsForRobot(
  orgname: string,
  robotname: string,
  repoPerms: IRepoPerm[],
  isUser = false,
) {
  const responses = await Promise.allSettled(
    repoPerms.map((repoPerm) =>
      updateRepoPermsForRobot(
        orgname,
        robotname,
        repoPerm.reponame,
        repoPerm.permission,
        isUser,
      ),
    ),
  );

  // Aggregate failed responses
  const errResponses = responses.filter(
    (r) => r.status == 'rejected',
  ) as PromiseRejectedResult[];

  // If errors, collect and throw
  if (errResponses.length > 0) {
    const bulkDeleteError = new BulkOperationError(
      'error deleting repository permissions',
    );
    for (const response of errResponses) {
      const reason = response.reason;
      bulkDeleteError.addError(reason.repository_name, reason);
    }
    throw bulkDeleteError;
  }

  return {response: responses, robotname: robotname};
}

export async function deleteRepoPermsForRobot(
  orgname: string,
  robotname: string,
  reponame: string,
  isUser = false,
) {
  const robotNameWithOrg = `${orgname}+${robotname}`;
  const deletePermsUrl = `/api/v1/repository/${orgname}/${reponame}/permissions/user/${robotNameWithOrg}`;
  const response: AxiosResponse = await axios.delete(deletePermsUrl);
  assertHttpCode(response.status, 204);
  return response.data;
}

export async function bulkDeleteRepoPermsForRobot(
  orgname: string,
  robotname: string,
  repoNames: string[],
  isUser: boolean,
) {
  const responses = await Promise.allSettled(
    repoNames.map((repoName) =>
      deleteRepoPermsForRobot(orgname, robotname, repoName, isUser),
    ),
  );

  // Aggregate failed responses
  const errResponses = responses.filter(
    (r) => r.status == 'rejected',
  ) as PromiseRejectedResult[];

  // If errors, collect and throw
  if (errResponses.length > 0) {
    const bulkDeleteError = new BulkOperationError(
      'error deleting repository permissions',
    );
    for (const response of errResponses) {
      const reason = response.reason;
      bulkDeleteError.addError(reason.repository_name, reason);
    }
    throw bulkDeleteError;
  }

  return {response: responses, robotname: robotname};
}

export async function createNewRobotForNamespace(
  orgname: string,
  robotname: string,
  description: string,
  isUser = false,
) {
  const namespacePath = isUser ? 'user' : `organization/${orgname}`;
  const createOrgRobotsUrl = `/api/v1/${namespacePath}/robots/${robotname}`;
  const payload = {description: description};
  const response: AxiosResponse = await axios.put(createOrgRobotsUrl, payload);
  assertHttpCode(response.status, 201);
  return response.data;
}

export async function deleteRobotAccount(orgname: string, robotname: string) {
  try {
    const robot = robotname.replace(orgname + '+', '');
    const deleteUrl = `/api/v1/organization/${orgname}/robots/${robot}`;
    const response: AxiosResponse = await axios.delete(deleteUrl);
    assertHttpCode(response.status, 204);
    return response.data;
  } catch (err) {
    throw new RobotDeleteError(
      'failed to delete robot account ',
      robotname,
      err,
    );
  }
}

export async function createRobotAccount(
  orgName: string,
  robotAccntName: string,
  description: string,
) {
  const response: AxiosResponse = await axios.put(
    `api/v1/organization/${orgName}/robots/${robotAccntName}`,
    {description: description},
  );
  assertHttpCode(response.status, 201);
  return response.data?.name;
}

export async function bulkDeleteRobotAccounts(
  orgname: string,
  robotaccounts: IRobot[],
) {
  const responses = await Promise.allSettled(
    robotaccounts.map((robot) => deleteRobotAccount(orgname, robot.name)),
  );

  // Aggregate failed responses
  const errResponses = responses.filter(
    (r) => r.status == 'rejected',
  ) as PromiseRejectedResult[];

  // If errors, collect and throw
  if (errResponses.length > 0) {
    const bulkDeleteError = new BulkOperationError(
      'error deleting robot accounts',
    );
    for (const response of errResponses) {
      const reason = response.reason;
      bulkDeleteError.addError(reason.robot, reason);
    }
    throw bulkDeleteError;
  }

  return responses;
}

export async function fetchRobotPermissionsForNamespace(
  orgName: string,
  robotName: string,
  isUser = false,
  signal: AbortSignal,
) {
  const robot = robotName.replace(orgName + '+', '');
  const userOrOrgPath = isUser ? 'user' : `organization/${orgName}`;
  const getRobotPermsUrl = `/api/v1/${userOrOrgPath}/robots/${robot}/permissions`;
  const response: AxiosResponse = await axios.get(getRobotPermsUrl, {signal});
  assertHttpCode(response.status, 200);
  return response.data?.permissions;
}

export async function fetchRobotAccountToken(
  orgName: string,
  robotName: string,
  isUser = false,
  signal: AbortSignal,
) {
  const robot = robotName.replace(orgName + '+', '');
  const userOrOrgPath = isUser ? 'user' : `organization/${orgName}`;
  const getRobotTokenUrl = `/api/v1/${userOrOrgPath}/robots/${robot}`;
  const response: AxiosResponse = await axios.get(getRobotTokenUrl, {signal});
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function regenerateRobotToken(
  orgName: string,
  robotName: string,
  isUser = false,
): Promise<IRobot[]> {
  const robot = robotName.replace(orgName + '+', '');
  const userOrOrgPath = isUser ? 'user' : `organization/${orgName}`;
  const updatePermsUrl = `/api/v1/${userOrOrgPath}/robots/${robot}/regenerate`;
  const response: AxiosResponse = await axios.post(updatePermsUrl, {});
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function fetchRobotFederationConfig(
  orgName: string,
  robotName: string,
  signal: AbortSignal,
) {
  const robot = robotName.replace(orgName + '+', '');
  const userOrOrgPath = `organization/${orgName}`;
  const getRobotFederationConfigUrl = `/api/v1/${userOrOrgPath}/robots/${robot}/federation`;
  const response: AxiosResponse = await axios.get(getRobotFederationConfigUrl, {
    signal,
  });
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function createRobotFederationConfig(
  orgName: string,
  robotName: string,
  federationConfig: IRobotFederationConfig[],
) {
  const robot = robotName.replace(orgName + '+', '');
  const userOrOrgPath = `organization/${orgName}`;
  const createRobotFederationConfigUrl = `/api/v1/${userOrOrgPath}/robots/${robot}/federation`;
  const response: AxiosResponse = await axios.post(
    createRobotFederationConfigUrl,
    federationConfig,
  );
  assertHttpCode(response.status, 200);
  return response.data;
}
