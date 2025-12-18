import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';

// Organization mirror configuration types
export interface OrgMirrorRootRule {
  rule_type: 'NONE' | 'INCLUDE_LIST' | 'EXCLUDE_LIST' | 'REGEX';
  rule_value: Record<string, string[]> | string;
  left_child?: OrgMirrorRootRule | null;
  right_child?: OrgMirrorRootRule | null;
}

export interface OrgMirrorConfig {
  is_enabled: boolean;
  external_reference: string;
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
  sync_interval: number;
  sync_start_date?: string;
  internal_robot: string;
  root_rule?: OrgMirrorRootRule | null;
  skopeo_timeout: number;
}

export interface OrgMirrorConfigResponse extends OrgMirrorConfig {
  sync_status:
    | 'NEVER_RUN'
    | 'SUCCESS'
    | 'FAIL'
    | 'SYNCING'
    | 'SYNC_NOW'
    | 'CANCEL';
  sync_expiration_date?: string | null;
  sync_retries_remaining?: number | null;
}

export interface DiscoveredRepository {
  repository_name: string;
  external_repo_name: string;
  status: string;
  message: string | null;
  created_repository: string | null;
}

export interface DiscoveredRepositoriesResponse {
  repositories: DiscoveredRepository[];
}

// API functions
export async function fetchOrgMirrorConfig(
  orgName: string,
  signal?: AbortSignal,
): Promise<OrgMirrorConfigResponse> {
  const response: AxiosResponse<OrgMirrorConfigResponse> = await axios.get(
    `/api/v1/organization/${orgName}/mirror`,
    {signal},
  );
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function createOrgMirrorConfig(
  orgName: string,
  config: OrgMirrorConfig,
): Promise<OrgMirrorConfigResponse> {
  const response: AxiosResponse<OrgMirrorConfigResponse> = await axios.post(
    `/api/v1/organization/${orgName}/mirror`,
    config,
  );
  assertHttpCode(response.status, 201);
  return response.data;
}

export async function updateOrgMirrorConfig(
  orgName: string,
  config: Partial<OrgMirrorConfig>,
): Promise<OrgMirrorConfigResponse> {
  const response: AxiosResponse<OrgMirrorConfigResponse> = await axios.put(
    `/api/v1/organization/${orgName}/mirror`,
    config,
  );
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function deleteOrgMirrorConfig(
  orgName: string,
  signal?: AbortSignal,
): Promise<void> {
  const response = await axios.delete(
    `/api/v1/organization/${orgName}/mirror`,
    {signal},
  );
  assertHttpCode(response.status, 204);
}

export async function triggerOrgMirrorSync(orgName: string): Promise<void> {
  const response = await axios.post(
    `/api/v1/organization/${orgName}/mirror/sync-now`,
  );
  assertHttpCode(response.status, 200);
}

export async function fetchDiscoveredRepositories(
  orgName: string,
  status?: string,
  signal?: AbortSignal,
): Promise<DiscoveredRepositoriesResponse> {
  const url = status
    ? `/api/v1/organization/${orgName}/mirror/repositories?status=${status}`
    : `/api/v1/organization/${orgName}/mirror/repositories`;
  const response: AxiosResponse<DiscoveredRepositoriesResponse> =
    await axios.get(url, {signal});
  assertHttpCode(response.status, 200);
  return response.data;
}

// Sync status labels for display
export const syncStatusLabels: Record<
  OrgMirrorConfigResponse['sync_status'],
  string
> = {
  NEVER_RUN: 'Scheduled',
  SYNC_NOW: 'Scheduled Now',
  FAIL: 'Failed',
  SYNCING: 'Syncing',
  SUCCESS: 'Success',
  CANCEL: 'Cancelled',
};
