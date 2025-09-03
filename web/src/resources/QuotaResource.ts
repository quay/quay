import axios from 'src/libs/axios';

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

// Fetch organization quota
export async function fetchOrganizationQuota(
  orgName: string,
  signal?: AbortSignal,
): Promise<IQuota[]> {
  const response = await axios.get(`/api/v1/organization/${orgName}/quota`, {
    signal,
  });
  return response.data;
}

// Create organization quota
export async function createOrganizationQuota(
  orgName: string,
  params: ICreateQuotaParams,
): Promise<void> {
  await axios.post(`/api/v1/organization/${orgName}/quota`, params);
}

// Update organization quota
export async function updateOrganizationQuota(
  orgName: string,
  quotaId: string,
  params: IUpdateQuotaParams,
): Promise<void> {
  await axios.put(`/api/v1/organization/${orgName}/quota/${quotaId}`, params);
}

// Delete organization quota
export async function deleteOrganizationQuota(
  orgName: string,
  quotaId: string,
): Promise<void> {
  await axios.delete(`/api/v1/organization/${orgName}/quota/${quotaId}`);
}

// Create quota limit
export async function createQuotaLimit(
  orgName: string,
  quotaId: string,
  params: ICreateQuotaLimitParams,
): Promise<void> {
  await axios.post(
    `/api/v1/organization/${orgName}/quota/${quotaId}/limit`,
    params,
  );
}

// Update quota limit
export async function updateQuotaLimit(
  orgName: string,
  quotaId: string,
  limitId: string,
  params: ICreateQuotaLimitParams,
): Promise<void> {
  await axios.put(
    `/api/v1/organization/${orgName}/quota/${quotaId}/limit/${limitId}`,
    params,
  );
}

// Delete quota limit
export async function deleteQuotaLimit(
  orgName: string,
  quotaId: string,
  limitId: string,
): Promise<void> {
  await axios.delete(
    `/api/v1/organization/${orgName}/quota/${quotaId}/limit/${limitId}`,
  );
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
