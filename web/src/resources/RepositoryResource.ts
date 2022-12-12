import {AxiosError, AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {
  assertHttpCode,
  BulkOperationError,
  ResourceError,
  throwIfError,
} from './ErrorHandling';
import {IAvatar} from './OrganizationResource';

export interface IRepository {
  namespace: string;
  name: string;
  description?: string;
  is_public?: boolean;
  kind?: string;
  state?: string;
  size?: number;
  last_modified?: number;
  popularity?: number;
  is_starred?: boolean;
  quota_report?: IQuotaReport;
}

export interface RepositoryCreationResponse {
  namespace: string;
  name: string;
  kind: string;
}

export interface IQuotaReport {
  quota_bytes: number;
  configured_quota: number;
}

export async function fetchAllRepos(
  namespaces: string[],
  flatten = false,
  signal: AbortSignal,
  next_page_token = null,
): Promise<IRepository[] | IRepository[][]> {
  const namespacedRepos = await Promise.all(
    namespaces.map((ns) => {
      return fetchRepositoriesForNamespace(ns, signal, next_page_token);
    }),
  );

  // Flatten responses to a single list of all repositories
  if (flatten) {
    return namespacedRepos.reduce(
      (allRepos, namespacedRepos) => allRepos.concat(namespacedRepos),
      [],
    );
  } else {
    return namespacedRepos;
  }
}

export async function fetchRepositoriesForNamespace(
  ns: string,
  signal: AbortSignal,
  next_page_token: string = null,
): Promise<IRepository[]> {
  const url = next_page_token
    ? `/api/v1/repository?next_page=${next_page_token}&last_modified=true&namespace=${ns}&public=true`
    : `/api/v1/repository?last_modified=true&namespace=${ns}&public=true`;
  const response: AxiosResponse = await axios.get(url, {signal});
  assertHttpCode(response.status, 200);

  const next_page = response.data?.next_page;
  const repos = response.data?.repositories as IRepository[];

  if (next_page) {
    const resp = await fetchRepositoriesForNamespace(ns, signal, next_page);
    return repos.concat(resp);
  }
  return repos as IRepository[];
}

export async function fetchRepositories() {
  // TODO: Add return type to AxiosResponse
  const response: AxiosResponse = await axios.get(
    `/api/v1/repository?last_modified=true&public=true`,
  );
  assertHttpCode(response.status, 200);
  return response.data?.repositories as IRepository[];
}

export interface RepositoryDetails {
  can_admin: boolean;
  can_write: boolean;
  description: string | null;
  is_free_account: boolean;
  is_organization: boolean;
  is_public: boolean;
  is_starred: boolean;
  kind: string | null;
  name: string | null;
  namespace: string | null;
  state: string | null;
  status_token: string | null;
  tag_expiration_s: number | null;
  trust_enabled: boolean;
}

export async function fetchRepositoryDetails(org: string, repo: string) {
  const response: AxiosResponse<RepositoryDetails> = await axios.get(
    `/api/v1/repository/${org}/${repo}?includeStats=false&includeTags=false`,
  );
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function createNewRepository(
  namespace: string,
  repository: string,
  visibility: string,
  description: string,
  repo_kind: string,
) {
  const newRepositoryApiUrl = `/api/v1/repository`;
  const response: AxiosResponse<RepositoryCreationResponse> = await axios.post(
    newRepositoryApiUrl,
    {
      namespace,
      repository,
      visibility,
      description,
      repo_kind,
    },
  );
  assertHttpCode(response.status, 201);
  return response.data;
}

export async function setRepositoryVisibility(
  namespace: string,
  repositoryName: string,
  visibility: string,
) {
  // TODO: Add return type to AxiosResponse
  const api = `/api/v1/repository/${namespace}/${repositoryName}/changevisibility`;
  const response: AxiosResponse = await axios.post(api, {
    visibility,
  });
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function bulkDeleteRepositories(repos: IRepository[]) {
  const responses = await Promise.allSettled(
    repos.map((repo) => deleteRepository(repo.namespace, repo.name)),
  );

  // Aggregate failed responses
  const errResponses = responses.filter(
    (r) => r.status == 'rejected',
  ) as PromiseRejectedResult[];

  // If errors, collect and throw
  if (errResponses.length > 0) {
    const bulkDeleteError = new BulkOperationError<RepoDeleteError>(
      'error deleting tags',
    );
    for (const response of errResponses) {
      const reason = response.reason as RepoDeleteError;
      bulkDeleteError.addError(reason.repo, reason);
    }
    throw bulkDeleteError;
  }
}

export interface RepoPermissionsResponse {
  permissions: Record<string, RepoMemberPermissions>;
}

export interface RepoMemberPermissions {
  role: RepoRole;
  name: string;
  avatar: IAvatar;
  is_robot?: boolean;
  is_org_member?: boolean;
}

export async function fetchUserRepoPermissions(org: string, repo: string) {
  const response: AxiosResponse<RepoPermissionsResponse> = await axios.get(
    `/api/v1/repository/${org}/${repo}/permissions/user/`,
  );
  return response.data.permissions;
}

export async function fetchTeamRepoPermissions(org: string, repo: string) {
  const response: AxiosResponse<RepoPermissionsResponse> = await axios.get(
    `/api/v1/repository/${org}/${repo}/permissions/team/`,
  );
  return response.data.permissions;
}

export interface RepoMember {
  org: string;
  repo: string;
  name: string;
  type: MemberType;
  role: RepoRole;
}

export enum RepoRole {
  read = 'read',
  write = 'write',
  admin = 'admin',
}

export enum MemberType {
  user = 'user',
  robot = 'robot',
  team = 'team',
}

export async function setRepoPermissions(role: RepoMember, newRole: RepoRole) {
  const type = role.type == MemberType.robot ? MemberType.user : role.type;
  try {
    await axios.put(
      `/api/v1/repository/${role.org}/${role.repo}/permissions/${type}/${role.name}`,
      {role: newRole},
    );
  } catch (err) {
    throw new ResourceError(
      'failed to set repository permissions',
      role.name,
      err,
    );
  }
}

export async function bulkSetRepoPermissions(
  roles: RepoMember[],
  newRole: RepoRole,
) {
  const responses = await Promise.allSettled(
    roles.map((role) => setRepoPermissions(role, newRole)),
  );
  throwIfError(responses);
}

export async function bulkDeleteRepoPermissions(roles: RepoMember[]) {
  const responses = await Promise.allSettled(
    roles.map((role) => deleteRepoPermissions(role)),
  );
  throwIfError(responses);
}

export async function deleteRepoPermissions(role: RepoMember) {
  const roleType = role.type == MemberType.robot ? MemberType.user : role.type;
  try {
    await axios.delete(
      `/api/v1/repository/${role.org}/${role.repo}/permissions/${roleType}/${role.name}`,
    );
  } catch (err) {
    throw new ResourceError(
      'failed to set repository permissions',
      role.name,
      err,
    );
  }
}

export class RepoDeleteError extends Error {
  error: Error;
  repo: string;
  constructor(message: string, repo: string, error: AxiosError) {
    super(message);
    this.repo = repo;
    this.error = error;
    Object.setPrototypeOf(this, RepoDeleteError.prototype);
  }
}

// Not returning response from deleting repository for now as
// it's not required but may want to add it in the future.
export async function deleteRepository(ns: string, name: string) {
  try {
    const response: AxiosResponse = await axios.delete(
      `/api/v1/repository/${ns}/${name}`,
    );
    assertHttpCode(response.status, 204);
  } catch (err) {
    throw new RepoDeleteError(
      'failed to delete repository',
      `${ns}/${name}`,
      err,
    );
  }
}
