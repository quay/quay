import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';

export interface RepositoryPolicy {
  blockUnsignedImages: boolean;
}

export async function fetchRepositoryPolicy(
  namespace: string,
  repository: string,
  signal: AbortSignal,
) {
  const response: AxiosResponse<RepositoryPolicy> = await axios.get(
    `/api/v1/repository/${namespace}/${repository}/policy/`,
    {signal},
  );
  return response.data;
}

export async function updateRepositoryPolicy(
  namespace: string,
  repository: string,
  policy: RepositoryPolicy,
) {
  console.log(policy);
  const response: AxiosResponse<RepositoryPolicy> = await axios.put(
    `/api/v1/repository/${namespace}/${repository}/policy/`,
    policy,
  );
  return response.data;
}
