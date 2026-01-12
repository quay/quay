import axios from 'src/libs/axios';
import {AxiosError} from 'axios';

/**
 * AI Settings for an organization
 */
export interface AISettings {
  description_generator_enabled: boolean;
  provider: string | null;
  model: string | null;
  endpoint: string | null;
  credentials_configured: boolean;
  credentials_verified: boolean;
}

/**
 * Request to update AI settings
 */
export interface UpdateAISettingsRequest {
  description_generator_enabled?: boolean;
  provider?: string;
  model?: string;
}

/**
 * Request to set AI credentials
 */
export interface SetAICredentialsRequest {
  provider: string;
  api_key: string;
  model?: string;
  endpoint?: string;
}

/**
 * Request to verify AI credentials
 */
export interface VerifyAICredentialsRequest {
  provider: string;
  api_key: string;
  model: string;
  endpoint?: string;
}

/**
 * Response from credential verification
 */
export interface VerifyAICredentialsResponse {
  valid: boolean;
  error?: string;
}

/**
 * Request to generate AI description
 */
export interface GenerateDescriptionRequest {
  tag: string;
  force_regenerate?: boolean;
}

/**
 * Response from description generation
 */
export interface GenerateDescriptionResponse {
  description: string;
  cached: boolean;
  manifest_digest: string;
  tag: string;
}

/**
 * Tag info for description generation
 */
export interface AIDescriptionTag {
  name: string;
  manifest_digest: string | null;
}

/**
 * Response from listing tags
 */
export interface ListAITagsResponse {
  tags: AIDescriptionTag[];
}

/**
 * Cached description response
 */
export interface CachedDescriptionResponse {
  description: string | null;
  cached: boolean;
  manifest_digest: string;
}

/**
 * Valid AI provider names
 */
export const VALID_PROVIDERS = [
  'anthropic',
  'openai',
  'google',
  'deepseek',
  'custom',
] as const;

export type AIProvider = (typeof VALID_PROVIDERS)[number];

/**
 * Custom error class for AI operations
 */
export class AIError extends Error {
  status: number;
  originalError: AxiosError;

  constructor(message: string, status: number, originalError: AxiosError) {
    super(message);
    this.name = 'AIError';
    this.status = status;
    this.originalError = originalError;
  }
}

/**
 * Fetch AI settings for an organization
 */
export async function fetchAISettings(orgName: string): Promise<AISettings> {
  const response = await axios.get(`/api/v1/organization/${orgName}/ai`);
  return response.data;
}

/**
 * Update AI settings for an organization
 */
export async function updateAISettings(
  orgName: string,
  settings: UpdateAISettingsRequest,
): Promise<AISettings> {
  const response = await axios.put(
    `/api/v1/organization/${orgName}/ai`,
    settings,
  );
  return response.data;
}

/**
 * Set AI credentials for an organization
 */
export async function setAICredentials(
  orgName: string,
  credentials: SetAICredentialsRequest,
): Promise<AISettings> {
  const response = await axios.put(
    `/api/v1/organization/${orgName}/ai/credentials`,
    credentials,
  );
  return response.data;
}

/**
 * Delete AI credentials for an organization
 */
export async function deleteAICredentials(orgName: string): Promise<void> {
  await axios.delete(`/api/v1/organization/${orgName}/ai/credentials`);
}

/**
 * Verify AI credentials
 */
export async function verifyAICredentials(
  orgName: string,
  request: VerifyAICredentialsRequest,
): Promise<VerifyAICredentialsResponse> {
  const response = await axios.post(
    `/api/v1/organization/${orgName}/ai/credentials/verify`,
    request,
  );
  return response.data;
}

/**
 * Generate AI description for a repository
 */
export async function generateAIDescription(
  namespace: string,
  repository: string,
  request: GenerateDescriptionRequest,
): Promise<GenerateDescriptionResponse> {
  const response = await axios.post(
    `/api/v1/repository/${namespace}/${repository}/ai/description`,
    request,
  );
  return response.data;
}

/**
 * List tags available for AI description generation
 */
export async function listAIDescriptionTags(
  namespace: string,
  repository: string,
): Promise<ListAITagsResponse> {
  const response = await axios.get(
    `/api/v1/repository/${namespace}/${repository}/ai/description/tags`,
  );
  return response.data;
}

/**
 * Get cached AI description
 */
export async function getCachedDescription(
  namespace: string,
  repository: string,
  manifestDigest: string,
): Promise<CachedDescriptionResponse> {
  const response = await axios.get(
    `/api/v1/repository/${namespace}/${repository}/ai/description/cached/${encodeURIComponent(
      manifestDigest,
    )}`,
  );
  return response.data;
}
