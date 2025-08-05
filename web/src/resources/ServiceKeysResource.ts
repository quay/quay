import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';

export interface IServiceKeyApproval {
  approval_type: string;
  approver?: {
    name: string;
    username: string;
    kind: string;
  };
  notes?: string;
}

export interface IServiceKey {
  kid: string;
  name?: string;
  service: string;
  created_date: string | number; // Can be ISO string or unix timestamp
  expiration_date?: string | number; // Can be ISO string or unix timestamp
  approval?: IServiceKeyApproval;
  metadata?: Record<string, unknown>;
}

export interface ServiceKeysResponse {
  keys: IServiceKey[];
}

export async function fetchServiceKeys(): Promise<IServiceKey[]> {
  const response: AxiosResponse<ServiceKeysResponse> = await axios.get(
    '/api/v1/superuser/keys',
  );
  assertHttpCode(response.status, 200);
  return response.data.keys;
}

export interface CreateServiceKeyRequest {
  service: string;
  name?: string;
  expiration: number | null;
  metadata?: Record<string, unknown>;
  notes?: string;
}

export async function createServiceKey(
  keyData: CreateServiceKeyRequest,
): Promise<IServiceKey> {
  const response: AxiosResponse<IServiceKey> = await axios.post(
    '/api/v1/superuser/keys',
    keyData,
  );
  assertHttpCode(response.status, 200);
  return response.data;
}

export interface UpdateServiceKeyRequest {
  name?: string;
  metadata?: Record<string, unknown>;
  expiration?: number | null;
}

export async function updateServiceKey(
  kid: string,
  keyData: UpdateServiceKeyRequest,
): Promise<IServiceKey> {
  const response: AxiosResponse<IServiceKey> = await axios.put(
    `/api/v1/superuser/keys/${kid}`,
    keyData,
  );
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function deleteServiceKey(kid: string): Promise<void> {
  const response: AxiosResponse = await axios.delete(
    `/api/v1/superuser/keys/${kid}`,
  );
  assertHttpCode(response.status, 204);
}

export async function approveServiceKey(kid: string): Promise<IServiceKey> {
  const response: AxiosResponse<IServiceKey> = await axios.post(
    `/api/v1/superuser/approvedkeys/${kid}`,
  );
  assertHttpCode(response.status, 200);
  return response.data;
}
