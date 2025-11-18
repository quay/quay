import axios from 'src/libs/axios';
import {AxiosError} from 'axios';

export interface IQuotaLimit {
  id: string;
  type: 'Warning' | 'Reject';
  limit_percent: number;
}

export interface IQuota {
  id: string;
  limit_bytes: number;
  limits: IQuotaLimit[];
}

export interface ICreateQuotaParams {
  limit_bytes: number;
}

export interface IUpdateQuotaParams {
  limit_bytes?: number;
  limit?: string;
}

export interface ICreateQuotaLimitParams {
  type: 'Warning' | 'Reject';
  threshold_percent: number;
}

export type QuotaViewMode = 'self' | 'organization' | 'superuser';

// Fetch quota based on view context
export async function fetchOrganizationQuota(
  orgName: string,
  signal?: AbortSignal,
  viewMode?: QuotaViewMode,
): Promise<IQuota[]> {
  try {
    // Build endpoint based on view context
    let endpoint: string;
    if (viewMode === 'self') {
      // User viewing their own quota (no username in path - auth determines user)
      endpoint = '/api/v1/user/quota';
    } else if (viewMode === 'superuser') {
      // Superuser managing a user's quota
      endpoint = `/api/v1/superuser/users/${orgName}/quota`;
    } else {
      // Organization quota (default)
      endpoint = `/api/v1/organization/${orgName}/quota`;
    }

    const response = await axios.get(endpoint, {
      signal,
    });
    return response.data;
  } catch (error: unknown) {
    // Handle AbortController cancellations gracefully
    if (error instanceof Error && error.name === 'CanceledError') {
      return [];
    }
    // Handle AxiosError specifically
    if (error instanceof AxiosError) {
      if (error.code === 'ERR_CANCELED') {
        return [];
      }
      // Return empty array for 404 (no quota configured) or permission errors
      if (error.response?.status === 404 || error.response?.status === 403) {
        return [];
      }
    }
    // Re-throw other errors
    throw error;
  }
}

// Create quota (only superusers can create quotas)
export async function createOrganizationQuota(
  orgName: string,
  params: ICreateQuotaParams,
  viewMode?: QuotaViewMode,
): Promise<void> {
  const endpoint =
    viewMode === 'superuser'
      ? `/api/v1/superuser/users/${orgName}/quota`
      : `/api/v1/organization/${orgName}/quota`;
  await axios.post(endpoint, params);
}

// Update quota (only superusers can update quotas)
export async function updateOrganizationQuota(
  orgName: string,
  quotaId: string,
  params: IUpdateQuotaParams,
  viewMode?: QuotaViewMode,
): Promise<void> {
  const endpoint =
    viewMode === 'superuser'
      ? `/api/v1/superuser/users/${orgName}/quota/${quotaId}`
      : `/api/v1/organization/${orgName}/quota/${quotaId}`;
  await axios.put(endpoint, params);
}

// Delete quota (only superusers can delete quotas)
export async function deleteOrganizationQuota(
  orgName: string,
  quotaId: string,
  viewMode?: QuotaViewMode,
): Promise<void> {
  const endpoint =
    viewMode === 'superuser'
      ? `/api/v1/superuser/users/${orgName}/quota/${quotaId}`
      : `/api/v1/organization/${orgName}/quota/${quotaId}`;
  await axios.delete(endpoint);
}

// Create quota limit (for organization or user quota)
export async function createQuotaLimit(
  orgName: string,
  quotaId: string,
  params: ICreateQuotaLimitParams,
): Promise<void> {
  const endpoint = `/api/v1/organization/${orgName}/quota/${quotaId}/limit`;
  await axios.post(endpoint, params);
}

// Update quota limit (for organization or user quota)
export async function updateQuotaLimit(
  orgName: string,
  quotaId: string,
  limitId: string,
  params: ICreateQuotaLimitParams,
): Promise<void> {
  const endpoint = `/api/v1/organization/${orgName}/quota/${quotaId}/limit/${limitId}`;
  await axios.put(endpoint, params);
}

// Delete quota limit (for organization or user quota)
export async function deleteQuotaLimit(
  orgName: string,
  quotaId: string,
  limitId: string,
): Promise<void> {
  const endpoint = `/api/v1/organization/${orgName}/quota/${quotaId}/limit/${limitId}`;
  await axios.delete(endpoint);
}

// Helper function to convert bytes to human readable format
export function bytesToHumanReadable(bytes: number): {
  value: number;
  unit: string;
} {
  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB'];
  let unitIndex = 0;
  let value = bytes;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex++;
  }

  return {
    value: Math.round(value * 100) / 100, // Round to 2 decimal places
    unit: units[unitIndex],
  };
}

// Helper function to convert human readable format to bytes
export function humanReadableToBytes(value: number, unit: string): number {
  const units = {
    B: 1,
    KiB: 1024,
    MiB: 1024 ** 2,
    GiB: 1024 ** 3,
    TiB: 1024 ** 4,
  };

  return Math.floor(value * (units[unit] || 1));
}
