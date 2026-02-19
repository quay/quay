import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';

// Sync status types for org mirroring
// Must match OrgMirrorStatus enum names in data/database.py
export type OrgMirrorSyncStatus =
  | 'NEVER_RUN'
  | 'SYNC_NOW'
  | 'FAIL'
  | 'SYNCING'
  | 'SUCCESS'
  | 'CANCEL';

// Source registry types
export type SourceRegistryType = 'harbor' | 'quay';

// Organization mirror configuration response from GET endpoint
export interface OrgMirrorConfig {
  is_enabled: boolean;
  external_registry_type: SourceRegistryType;
  external_registry_url: string;
  external_namespace: string;
  external_registry_username: string | null;
  external_registry_config: {
    verify_tls?: boolean;
    proxy?: {
      http_proxy: string | null;
      https_proxy: string | null;
      no_proxy: string | null;
    };
  };
  repository_filters: string[];
  robot_username: string | null;
  visibility: string;
  sync_interval: number;
  sync_start_date: string | null;
  sync_expiration_date: string | null;
  sync_status: OrgMirrorSyncStatus;
  sync_retries_remaining: number;
  skopeo_timeout: number;
  creation_date: string | null;
}

// Request body for creating org mirror config
export interface CreateOrgMirrorConfig {
  external_registry_type: SourceRegistryType;
  external_registry_url: string;
  external_namespace: string;
  robot_username: string;
  visibility: string;
  sync_interval: number;
  sync_start_date: string;
  is_enabled?: boolean;
  external_registry_username?: string | null;
  external_registry_password?: string | null;
  external_registry_config?: {
    verify_tls?: boolean;
    proxy?: {
      http_proxy?: string | null;
      https_proxy?: string | null;
      no_proxy?: string | null;
    };
  };
  repository_filters?: string[];
  skopeo_timeout?: number;
}

// Request body for updating org mirror config (all fields optional)
export type UpdateOrgMirrorConfig = Partial<CreateOrgMirrorConfig>;

// Single discovered repository
export interface OrgMirrorRepository {
  name: string;
  sync_status: string;
  discovery_date: string | null;
  last_sync_date: string | null;
  status_message: string | null;
  quay_repository: string | null;
}

// Paginated response for discovered repositories
export interface OrgMirrorReposResponse {
  repositories: OrgMirrorRepository[];
  page: number;
  limit: number;
  total: number;
  has_next: boolean;
}

// Verify connection response
export interface OrgMirrorVerifyResponse {
  success: boolean;
  message: string;
}

// API functions

export const getOrgMirrorConfig = async (
  orgName: string,
): Promise<OrgMirrorConfig> => {
  const response: AxiosResponse<OrgMirrorConfig> = await axios.get(
    `/api/v1/organization/${orgName}/mirror`,
  );
  assertHttpCode(response.status, 200);
  return response.data;
};

export const createOrgMirrorConfig = async (
  orgName: string,
  config: CreateOrgMirrorConfig,
): Promise<void> => {
  const response = await axios.post(
    `/api/v1/organization/${orgName}/mirror`,
    config,
  );
  assertHttpCode(response.status, 201);
};

export const updateOrgMirrorConfig = async (
  orgName: string,
  config: UpdateOrgMirrorConfig,
): Promise<void> => {
  const response = await axios.put(
    `/api/v1/organization/${orgName}/mirror`,
    config,
  );
  assertHttpCode(response.status, 200);
};

export const deleteOrgMirrorConfig = async (orgName: string): Promise<void> => {
  const response = await axios.delete(`/api/v1/organization/${orgName}/mirror`);
  assertHttpCode(response.status, 204);
};

export const syncOrgMirrorNow = async (orgName: string): Promise<void> => {
  const response = await axios.post(
    `/api/v1/organization/${orgName}/mirror/sync-now`,
  );
  assertHttpCode(response.status, 204);
};

export const cancelOrgMirrorSync = async (orgName: string): Promise<void> => {
  const response = await axios.post(
    `/api/v1/organization/${orgName}/mirror/sync-cancel`,
  );
  assertHttpCode(response.status, 204);
};

export const verifyOrgMirrorConnection = async (
  orgName: string,
): Promise<OrgMirrorVerifyResponse> => {
  const response: AxiosResponse<OrgMirrorVerifyResponse> = await axios.post(
    `/api/v1/organization/${orgName}/mirror/verify`,
  );
  assertHttpCode(response.status, 200);
  return response.data;
};

export const getOrgMirrorRepos = async (
  orgName: string,
  page = 1,
  limit = 100,
): Promise<OrgMirrorReposResponse> => {
  const response: AxiosResponse<OrgMirrorReposResponse> = await axios.get(
    `/api/v1/organization/${orgName}/mirror/repositories`,
    {params: {page, limit}},
  );
  assertHttpCode(response.status, 200);
  return response.data;
};

// Status display labels
// Keys must match OrgMirrorStatus enum names from the backend
export const orgMirrorStatusLabels: Record<OrgMirrorSyncStatus, string> = {
  NEVER_RUN: 'Scheduled',
  SYNC_NOW: 'Scheduled Now',
  FAIL: 'Failed',
  SYNCING: 'Syncing',
  SUCCESS: 'Success',
  CANCEL: 'Cancelled',
};

// Status color mapping for PatternFly labels
export const orgMirrorStatusColors: Record<
  OrgMirrorSyncStatus,
  'blue' | 'green' | 'red' | 'cyan' | 'orange' | 'grey'
> = {
  NEVER_RUN: 'blue',
  SYNC_NOW: 'cyan',
  FAIL: 'red',
  SYNCING: 'blue',
  SUCCESS: 'green',
  CANCEL: 'orange',
};
