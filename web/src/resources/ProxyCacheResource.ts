import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';
import {IProxyCacheConfig} from 'src/hooks/UseProxyCache';
import {AxiosResponse} from 'axios';

export async function fetchProxyCacheConfig(org: string, signal?: AbortSignal) {
  const proxyCacheConfigUrl = `/api/v1/organization/${org}/proxycache`;
  const proxyResponse = await axios.get(proxyCacheConfigUrl, {signal});
  assertHttpCode(proxyResponse.status, 200);
  return proxyResponse.data;
}

export async function validateProxyCacheConfig(
  proxyCacheConfig: IProxyCacheConfig,
) {
  const proxyCacheConfigUrl = `/api/v1/organization/${proxyCacheConfig.org_name}/validateproxycache`;
  const payload = {
    ...proxyCacheConfig,
    upstream_registry_username:
      proxyCacheConfig.upstream_registry_username || null,
    upstream_registry_password:
      proxyCacheConfig.upstream_registry_password || null,
  };
  const proxyResponse = await axios.post(proxyCacheConfigUrl, payload);
  assertHttpCode(proxyResponse.status, 202);
  return proxyResponse.data;
}

export async function deleteProxyCacheConfig(
  org: string,
  signal?: AbortSignal,
) {
  const proxyCacheConfigUrl = `/api/v1/organization/${org}/proxycache`;
  const proxyResponse = await axios.delete(proxyCacheConfigUrl, {signal});
  assertHttpCode(proxyResponse.status, 201);
  return proxyResponse.data;
}

export async function createProxyCacheConfig(
  proxyCacheConfig: IProxyCacheConfig,
) {
  const createProxyCacheConfigUrl = `/api/v1/organization/${proxyCacheConfig.org_name}/proxycache`;
  const payload = {
    ...proxyCacheConfig,
    upstream_registry_username:
      proxyCacheConfig.upstream_registry_username || null,
    upstream_registry_password:
      proxyCacheConfig.upstream_registry_password || null,
  };
  const response: AxiosResponse = await axios.post(
    createProxyCacheConfigUrl,
    payload,
  );
  assertHttpCode(response.status, 201);
  return response.data;
}
