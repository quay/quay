import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';

export interface ImmutabilityPolicy {
  uuid?: string;
  tagPattern: string;
  tagPatternMatches: boolean;
}

// Namespace (Organization) API functions

export async function fetchNamespaceImmutabilityPolicies(
  namespace: string,
  signal: AbortSignal,
) {
  const namespaceUrl = `/api/v1/organization/${namespace}/immutabilitypolicy/`;
  const response: AxiosResponse = await axios.get(namespaceUrl, {signal});
  assertHttpCode(response.status, 200);
  const res = response.data.policies as ImmutabilityPolicy[];
  return res;
}

export async function createNamespaceImmutabilityPolicy(
  namespace: string,
  policy: Omit<ImmutabilityPolicy, 'uuid'>,
) {
  const namespaceUrl = `/api/v1/organization/${namespace}/immutabilitypolicy/`;
  const response = await axios.post(namespaceUrl, policy);
  assertHttpCode(response.status, 201);
  return response.data as {uuid: string};
}

export async function updateNamespaceImmutabilityPolicy(
  namespace: string,
  policy: ImmutabilityPolicy,
) {
  const namespaceUrl = `/api/v1/organization/${namespace}/immutabilitypolicy/${policy.uuid}`;
  const response = await axios.put(namespaceUrl, policy);
  assertHttpCode(response.status, 204);
}

export async function deleteNamespaceImmutabilityPolicy(
  namespace: string,
  uuid: string,
) {
  const namespaceUrl = `/api/v1/organization/${namespace}/immutabilitypolicy/${uuid}`;
  const response = await axios.delete(namespaceUrl);
  assertHttpCode(response.status, 200);
}

// Repository API functions

export async function fetchRepositoryImmutabilityPolicies(
  organizationName: string,
  repoName: string,
  signal: AbortSignal,
) {
  const repositoryUrl = `/api/v1/repository/${organizationName}/${repoName}/immutabilitypolicy/`;
  const response: AxiosResponse = await axios.get(repositoryUrl, {signal});
  assertHttpCode(response.status, 200);
  const res = response.data.policies as ImmutabilityPolicy[];
  return res;
}

export async function createRepositoryImmutabilityPolicy(
  organizationName: string,
  repoName: string,
  policy: Omit<ImmutabilityPolicy, 'uuid'>,
) {
  const repositoryUrl = `/api/v1/repository/${organizationName}/${repoName}/immutabilitypolicy/`;
  const response = await axios.post(repositoryUrl, policy);
  assertHttpCode(response.status, 201);
  return response.data as {uuid: string};
}

export async function updateRepositoryImmutabilityPolicy(
  organizationName: string,
  repoName: string,
  policy: ImmutabilityPolicy,
) {
  const repositoryUrl = `/api/v1/repository/${organizationName}/${repoName}/immutabilitypolicy/${policy.uuid}`;
  const response = await axios.put(repositoryUrl, policy);
  assertHttpCode(response.status, 204);
}

export async function deleteRepositoryImmutabilityPolicy(
  organizationName: string,
  repoName: string,
  uuid: string,
) {
  const repositoryUrl = `/api/v1/repository/${organizationName}/${repoName}/immutabilitypolicy/${uuid}`;
  const response = await axios.delete(repositoryUrl);
  assertHttpCode(response.status, 200);
}
