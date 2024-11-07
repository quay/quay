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
  const proxyResponse = await axios.post(proxyCacheConfigUrl, proxyCacheConfig);
  assertHttpCode(proxyResponse.status, 202);
  return proxyResponse.data;
}

export async function deleteProxyCacheConfig(org: string, signal?: AbortSignal) {
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
    upstream_registry: proxyCacheConfig.upstream_registry,
    expiration_s: proxyCacheConfig.expiration_s,
    insecure: proxyCacheConfig.insecure,
    org_name: proxyCacheConfig.org_name,
    upstream_registry_username: proxyCacheConfig.upstream_registry_username,
    upstream_registry_password: proxyCacheConfig.upstream_registry_password,
  };

  const response: AxiosResponse = await axios.post(
    createProxyCacheConfigUrl,
    payload,
  );
  assertHttpCode(response.status, 201);
  return response.data;
}