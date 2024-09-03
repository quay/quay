import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';
import {AutoPruneMethod} from './NamespaceAutoPruneResource';

export interface RepositoryAutoPrunePolicy {
  method: AutoPruneMethod;
  uuid?: string;
  value?: string | number;
  tagPattern?: string;
  tagPatternMatches?: boolean;
}

export async function fetchRepositoryAutoPrunePolicies(
  organizationName: string,
  repoName: string,
  signal: AbortSignal,
) {
  const repositoryAutoPruneUrl = `/api/v1/repository/${organizationName}/${repoName}/autoprunepolicy/`;
  const response: AxiosResponse = await axios.get(repositoryAutoPruneUrl, {
    signal,
  });
  assertHttpCode(response.status, 200);
  const res = response.data.policies as RepositoryAutoPrunePolicy[];
  return res;
}

export async function createRepositoryAutoPrunePolicy(
  organizationName: string,
  repoName: string,
  policy: RepositoryAutoPrunePolicy,
) {
  const repositoryAutoPruneUrl = `/api/v1/repository/${organizationName}/${repoName}/autoprunepolicy/`;
  const response = await axios.post(repositoryAutoPruneUrl, policy);
  assertHttpCode(response.status, 201);
}

export async function updateRepositoryAutoPrunePolicy(
  organizationName: string,
  repoName: string,
  policy: RepositoryAutoPrunePolicy,
) {
  const repositoryAutoPruneUrl = `/api/v1/repository/${organizationName}/${repoName}/autoprunepolicy/${policy.uuid}`;
  const response = await axios.put(repositoryAutoPruneUrl, policy);
  assertHttpCode(response.status, 204);
}

export async function deleteRepositoryAutoPrunePolicy(
  organizationName: string,
  repoName: string,
  uuid: string,
) {
  const repositoryAutoPruneUrl = `/api/v1/repository/${organizationName}/${repoName}/autoprunepolicy/${uuid}`;
  const response = await axios.delete(repositoryAutoPruneUrl);
  assertHttpCode(response.status, 200);
}
