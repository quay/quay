import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';

export enum AutoPruneMethod {
  NONE = 'none',
  TAG_NUMBER = 'number_of_tags',
  TAG_CREATION_DATE = 'creation_date',
}

export interface NamespaceAutoPrunePolicy {
  method: AutoPruneMethod;
  uuid?: string;
  value?: string | number;
  tagPattern?: string;
  tagPatternMatches?: boolean;
}

export async function fetchNamespaceAutoPrunePolicies(
  namespace: string,
  isUser: boolean,
  signal: AbortSignal,
) {
  const namespaceUrl = isUser
    ? '/api/v1/user/autoprunepolicy/'
    : `/api/v1/organization/${namespace}/autoprunepolicy/`;
  const response: AxiosResponse = await axios.get(namespaceUrl, {signal});
  assertHttpCode(response.status, 200);
  const res = response.data.policies as NamespaceAutoPrunePolicy[];
  return res;
}

export async function createNamespaceAutoPrunePolicy(
  namespace: string,
  policy: NamespaceAutoPrunePolicy,
  isUser: boolean,
) {
  const namespaceUrl = isUser
    ? '/api/v1/user/autoprunepolicy/'
    : `/api/v1/organization/${namespace}/autoprunepolicy/`;
  const response = await axios.post(namespaceUrl, policy);
  assertHttpCode(response.status, 201);
}

export async function updateNamespaceAutoPrunePolicy(
  namespace: string,
  policy: NamespaceAutoPrunePolicy,
  isUser: boolean,
) {
  const namespaceUrl = isUser
    ? `/api/v1/user/autoprunepolicy/${policy.uuid}`
    : `/api/v1/organization/${namespace}/autoprunepolicy/${policy.uuid}`;
  const response = await axios.put(namespaceUrl, policy);
  assertHttpCode(response.status, 204);
}

export async function deleteNamespaceAutoPrunePolicy(
  namespace: string,
  uuid: string,
  isUser: boolean,
) {
  const namespaceUrl = isUser
    ? `/api/v1/user/autoprunepolicy/${uuid}`
    : `/api/v1/organization/${namespace}/autoprunepolicy/${uuid}`;
  const response = await axios.delete(namespaceUrl);
  assertHttpCode(response.status, 200);
}
