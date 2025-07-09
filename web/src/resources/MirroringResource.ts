import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';

// Mirroring configuration types
export interface MirroringConfig {
  is_enabled: boolean;
  external_reference: string;
  external_registry_username?: string | null;
  external_registry_password?: string | null;
  robot_username: string;
  external_registry_config: {
    verify_tls: boolean;
    unsigned_images: boolean;
    proxy: {
      http_proxy: string | null;
      https_proxy: string | null;
      no_proxy: string | null;
    };
  };
  sync_start_date: string;
  sync_interval: number;
  root_rule: {
    rule_kind: string;
    rule_value: string[];
  };
}

export interface MirroringConfigResponse extends MirroringConfig {
  sync_status:
    | 'NEVER_RUN'
    | 'SYNC_NOW'
    | 'SYNC_FAILED'
    | 'SYNCING'
    | 'SYNC_SUCCESS';
  last_sync: string;
  last_error: string;
  status_message: string;
  mirror_type: string;
  external_reference: string;
  external_registry_username: string | null;
  sync_expiration_date: string | null;
  sync_retries_remaining: number | null;
  robot_username: string;
}

// Date conversion utilities
export const timestampToISO = (ts: number): string => {
  const dt = new Date(ts * 1000).toISOString();
  return dt.split('.')[0] + 'Z'; // Remove milliseconds
};

export const timestampFromISO = (dt: string): number => {
  return Math.floor(new Date(dt).getTime() / 1000);
};

// API functions
export const getMirrorConfig = async (
  namespace: string,
  repoName: string,
): Promise<MirroringConfigResponse> => {
  const response: AxiosResponse<MirroringConfigResponse> = await axios.get(
    `/api/v1/repository/${namespace}/${repoName}/mirror`,
  );
  assertHttpCode(response.status, 200);
  return response.data;
};

export const createMirrorConfig = async (
  namespace: string,
  repoName: string,
  config: MirroringConfig,
): Promise<MirroringConfigResponse> => {
  const response: AxiosResponse<MirroringConfigResponse> = await axios.post(
    `/api/v1/repository/${namespace}/${repoName}/mirror`,
    config,
  );
  assertHttpCode(response.status, 201);
  return response.data;
};

export const updateMirrorConfig = async (
  namespace: string,
  repoName: string,
  config: Partial<MirroringConfig>,
): Promise<MirroringConfigResponse> => {
  const response: AxiosResponse<MirroringConfigResponse> = await axios.put(
    `/api/v1/repository/${namespace}/${repoName}/mirror`,
    config,
  );
  assertHttpCode(response.status, 201);
  return response.data;
};

export const toggleMirroring = async (
  namespace: string,
  repoName: string,
  isEnabled: boolean,
): Promise<MirroringConfigResponse> => {
  return updateMirrorConfig(namespace, repoName, {is_enabled: isEnabled});
};

export const syncMirror = async (
  namespace: string,
  repoName: string,
): Promise<void> => {
  const response = await axios.post(
    `/api/v1/repository/${namespace}/${repoName}/mirror/sync-now`,
  );
  assertHttpCode(response.status, 204);
};

export const cancelSync = async (
  namespace: string,
  repoName: string,
): Promise<void> => {
  const response = await axios.post(
    `/api/v1/repository/${namespace}/${repoName}/mirror/sync-cancel`,
  );
  assertHttpCode(response.status, 204);
};

// Status message mapping
export const statusLabels: Record<
  MirroringConfigResponse['sync_status'],
  string
> = {
  NEVER_RUN: 'Scheduled',
  SYNC_NOW: 'Scheduled Now',
  SYNC_FAILED: 'Failed',
  SYNCING: 'Syncing',
  SYNC_SUCCESS: 'Success',
};
