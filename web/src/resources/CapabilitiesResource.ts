import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';

export interface SparseManifestsCapabilities {
  supported: boolean;
  required_architectures: string[];
  optional_architectures_allowed: boolean;
}

export interface RegistryCapabilities {
  sparse_manifests: SparseManifestsCapabilities;
  mirror_architectures: string[];
}

export async function fetchRegistryCapabilities(): Promise<RegistryCapabilities> {
  const response: AxiosResponse<RegistryCapabilities> = await axios.get(
    '/api/v1/registry/capabilities',
  );
  assertHttpCode(response.status, 200);
  return response.data;
}
